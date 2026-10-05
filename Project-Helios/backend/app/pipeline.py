import json
from datetime import datetime
import numpy as np
import networkx as nx
from backend.app.ingestion.parser import DataParser
from backend.app.features.feature_engineering import FeatureEngineer
from backend.app.ml.anomaly import AnomalyDetector
from backend.app.ml.clustering import EntityClusterer
from backend.app.graph.graph_builder import GraphBuilder
import os
import time

class Pipeline:
    def __init__(self, input_path: str, output_dir: str):
        self.input_path = input_path
        self.output_dir = output_dir
        self.parser = DataParser()
        # Look for ground truth in the same directory as input
        self.gt_path = os.path.join(os.path.dirname(input_path), "ground_truth.json")

    def run(self):
        start_time = time.time()
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 1. Ingest & Normalize
        records = self.parser.load_dataset(self.input_path)
        summary = self.parser.summary()
        
        if not records:
            print("No valid records found. Exiting.")
            return

        unique_ips = set(r.src_ip for r in records).union(r.dst_ip for r in records)
        unique_txids = set(r.txid for r in records)
        unique_addresses = set(addr for r in records for addr in r.addresses)

        # 2. Graph Building
        gb = GraphBuilder(records)
        graph = gb.build()
        graph_summary = gb.get_summary()
        
        gs_file = os.path.join(self.output_dir, f"latest_graph_summary.json")
        with open(gs_file, 'w') as f:
            json.dump(graph_summary, f, indent=2)
            
        graphml_file = os.path.join(self.output_dir, f"latest_graph.graphml")
        nx.write_graphml(graph, graphml_file)

        # 3. Features
        fe = FeatureEngineer(records, graph)
        features = fe.extract_features()
        
        # 4. Anomaly Detection
        detector = AnomalyDetector(contamination=0.26) # 25% of population are planted scenarios
        anomaly_results = detector.fit_predict(features)
        
        anomalies_count = sum(1 for res in anomaly_results.values() if res["is_anomaly"])

        # 5. Clustering
        clusterer = EntityClusterer(eps=1.5, min_samples=3)
        cluster_results = clusterer.fit_predict(features)
        
        real_clusters = set(c for c in cluster_results.values() if c != -1)
        noise_count = sum(1 for c in cluster_results.values() if c == -1)

        # 6. Generate Ranked Alerts
        alerts = []
        alert_counter = 1
        
        # Calculate percentiles for robust explanations
        def get_pct(feature_name, pct):
            return np.percentile([f[feature_name] for f in features.values()], pct) if features else 0

        p90_tx_vel = get_pct("tx_velocity", 90)
        p90_amt_var = get_pct("amount_variance", 90)
        p90_fan_out = get_pct("fan_out", 90)
        p90_nhood = get_pct("neighborhood_size", 90)
        p10_addr_ratio = get_pct("address_to_tx_ratio", 10) # lower is more reuse
        p90_ip_div = get_pct("dst_ip_diversity", 90)
        
        for entity, a_res in anomaly_results.items():
            if a_res["is_anomaly"]:
                cluster_id = cluster_results.get(entity, -1)
                feats = features[entity]
                
                reasons = []
                if feats["tx_velocity"] >= p90_tx_vel and p90_tx_vel > 0:
                    reasons.append(f"Transaction velocity observed at the top decile of the comparison population ({feats['tx_velocity']:.2f}). Contributes to the anomalous behavioral profile.")
                if feats["dst_ip_diversity"] >= p90_ip_div and p90_ip_div > 1:
                    reasons.append(f"Destination IP diversity observed at the top decile of the comparison population ({feats['dst_ip_diversity']}). Contributes to the anomalous behavioral profile.")
                if feats["amount_variance"] >= p90_amt_var and p90_amt_var > 0:
                    reasons.append(f"Extreme transaction amount variance observed. Contributes to the anomalous behavioral profile.")
                if feats["address_to_tx_ratio"] <= p10_addr_ratio and p10_addr_ratio < 1.0:
                    reasons.append(f"Highly concentrated address reuse observed (Ratio: {feats['address_to_tx_ratio']:.2f}). Contributes to the anomalous behavioral profile.")
                if feats.get("fan_out", 0) >= p90_fan_out and p90_fan_out > 0:
                    reasons.append(f"Graph fan-out observed at the top decile of the comparison population ({feats['fan_out']}). Contributes to the anomalous structural profile.")
                if feats.get("neighborhood_size", 0) >= p90_nhood and p90_nhood > 0:
                    reasons.append(f"Unusually large graph neighborhood observed ({feats['neighborhood_size']}). Contributes to the anomalous structural profile.")
                
                if not reasons:
                    reasons.append("Unusual statistical profile detected by ML engine.")
                    
                alerts.append({
                    "alert_id": f"A-{alert_counter:03d}",
                    "entity_id": entity,
                    "anomaly_score": a_res["anomaly_score"],
                    "confidence": a_res["anomaly_score"],
                    "cluster_id": cluster_id,
                    "reasons": reasons,
                    "model": "IsolationForest",
                    "features": feats
                })
                alert_counter += 1
                
        alerts.sort(key=lambda x: x["anomaly_score"], reverse=True)

        # 7. Evaluate against Ground Truth (Scenario Validation)
        gt_data = {}
        scenario_eval = {}
        if os.path.exists(self.gt_path):
            with open(self.gt_path, 'r') as f:
                gt_data = json.load(f)
                
            # Evaluate
            alert_entities = set(a["entity_id"] for a in alerts)
            planted_scenarios = {} # scenario_type -> list of IPs
            detected_scenarios = {} # scenario_type -> list of detected IPs
            
            for ip, info in gt_data.items():
                stype = info["scenario_type"]
                planted_scenarios.setdefault(stype, []).append(ip)
                if ip in alert_entities:
                    detected_scenarios.setdefault(stype, []).append(ip)
                    
            for stype in planted_scenarios.keys():
                planted = len(planted_scenarios[stype])
                detected = len(detected_scenarios.get(stype, []))
                scenario_eval[stype] = {
                    "planted": planted,
                    "detected": detected,
                    "recall": detected / planted if planted > 0 else 0
                }
            
            # Save evaluation report
            eval_file = os.path.join(self.output_dir, "scenario_results.json")
            with open(eval_file, 'w') as f:
                json.dump(scenario_eval, f, indent=2)

        # 8. Save outputs
        output_file = os.path.join(self.output_dir, f"latest_alerts.json")
        with open(output_file, 'w') as f:
            json.dump({
                "summary": summary,
                "stats": {
                    "unique_ips": len(unique_ips),
                    "unique_txids": len(unique_txids),
                    "unique_addresses": len(unique_addresses)
                },
                "alerts": alerts
            }, f, indent=2)

        end_time = time.time()
        runtime = end_time - start_time

        # Demo Report JSON
        demo_report = {
            "dataset_type": "controlled development fixture",
            "records_processed": summary['valid_records'],
            "unique_ips": len(unique_ips),
            "unique_txids": len(unique_txids),
            "unique_addresses": len(unique_addresses),
            "graph_nodes": graph_summary['num_nodes'],
            "graph_edges": graph_summary['num_edges'],
            "feature_count": len(list(features.values())[0]) if features else 0,
            "feature_names": list(list(features.values())[0].keys()) if features else [],
            "anomaly_model": "IsolationForest",
            "anomaly_count": anomalies_count,
            "clustering_model": "DBSCAN",
            "cluster_count": len(real_clusters),
            "noise_count": noise_count,
            "runtime": runtime,
            "top_alerts": alerts[:3],
            "scenario_validation": scenario_eval
        }
        
        demo_json_file = os.path.join(self.output_dir, "demo_report.json")
        with open(demo_json_file, 'w') as f:
            json.dump(demo_report, f, indent=2)

        # Demo Report TXT
        demo_txt_file = os.path.join(self.output_dir, "demo_report.txt")
        with open(demo_txt_file, 'w') as f:
            f.write("========================================\n")
            f.write("SIH26146 INTELLIGENCE PIPELINE\n")
            f.write("CONTROLLED DEVELOPMENT FIXTURE\n")
            f.write("========================================\n\n")
            f.write(f"Runtime: {runtime:.2f} seconds\n")
            f.write(f"Records processed: {summary['valid_records']}\n")
            f.write(f"Unique IPs: {len(unique_ips)}\n")
            f.write(f"Unique TXIDs: {len(unique_txids)}\n")
            f.write(f"Unique addresses: {len(unique_addresses)}\n")
            f.write(f"Graph nodes: {graph_summary['num_nodes']}\n")
            f.write(f"Graph edges: {graph_summary['num_edges']}\n")
            f.write(f"Features: {len(list(features.values())[0]) if features else 0}\n\n")
            
            if scenario_eval:
                f.write("----------------------------------------\n")
                f.write("SCENARIO VALIDATION (GROUND TRUTH)\n")
                f.write("----------------------------------------\n")
                for stype, metrics in scenario_eval.items():
                    f.write(f"{stype}: {metrics['detected']}/{metrics['planted']} detected ({metrics['recall']*100:.0f}%)\n")
                f.write("\n")
                
            f.write("----------------------------------------\n")
            f.write("ANOMALY DETECTION (Isolation Forest)\n")
            f.write("----------------------------------------\n")
            f.write(f"Anomalies: {anomalies_count}\n\n")
            f.write("----------------------------------------\n")
            f.write("ENTITY CLUSTERING (DBSCAN)\n")
            f.write("----------------------------------------\n")
            f.write(f"Clusters: {len(real_clusters)}\n")
            f.write(f"Noise: {noise_count}\n\n")
            f.write("----------------------------------------\n")
            f.write("TOP ALERTS\n")
            f.write("----------------------------------------\n")
            for alert in alerts[:3]:
                f.write(f"\n{alert['alert_id']}\n")
                f.write(f"Entity: {alert['entity_id']}\n")
                f.write(f"Confidence: {alert['confidence']:.2f}\n")
                f.write(f"Anomaly score: {alert['anomaly_score']:.2f}\n")
                cluster_str = f"{alert['cluster_id']}" if alert['cluster_id'] != -1 else "noise / not assigned to a cluster"
                f.write(f"Cluster: {cluster_str}\n")
                f.write("Evidence:\n")
                for r in alert['reasons']:
                    f.write(f"- {r}\n")
            f.write("\n========================================\n")

        with open(demo_txt_file, 'r') as f:
            print(f.read())
