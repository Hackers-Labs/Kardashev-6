import numpy as np
import networkx as nx
from typing import List, Dict, Optional
from backend.app.models import CanonicalRecord

class FeatureEngineer:
    def __init__(self, records: List[CanonicalRecord], graph: Optional[nx.DiGraph] = None):
        self.records = records
        self.graph = graph
        self.entity_features = {}
        
    def extract_features(self) -> Dict[str, Dict[str, float]]:
        ip_stats = {}
        
        for r in self.records:
            if r.src_ip not in ip_stats:
                ip_stats[r.src_ip] = {
                    "tx_count": 0,
                    "total_amount": 0.0,
                    "max_amount": 0.0,
                    "amounts": [],
                    "dst_ips": set(),
                    "dst_ports": set(),
                    "addresses": set(),
                    "timestamps": []
                }
            
            stats = ip_stats[r.src_ip]
            stats["tx_count"] += 1
            
            tx_amount = sum(r.amounts)
            stats["total_amount"] += tx_amount
            if tx_amount > stats["max_amount"]:
                stats["max_amount"] = tx_amount
            stats["amounts"].append(tx_amount)
            
            stats["dst_ips"].add(r.dst_ip)
            stats["dst_ports"].add(r.dst_port)
            stats["addresses"].update(r.addresses)
            stats["timestamps"].append(r.timestamp)

        for ip, stats in ip_stats.items():
            amounts = stats["amounts"]
            timestamps = sorted(stats["timestamps"])
            
            # Temporal features
            inter_arrivals = []
            for i in range(1, len(timestamps)):
                diff = (timestamps[i] - timestamps[i-1]).total_seconds()
                inter_arrivals.append(diff)
                
            if len(timestamps) > 1:
                duration_hours = (timestamps[-1] - timestamps[0]).total_seconds() / 3600.0
                tx_velocity = stats["tx_count"] / duration_hours if duration_hours > 0 else float(stats["tx_count"])
            else:
                tx_velocity = 0.0
                
            inter_arrival_avg = float(np.mean(inter_arrivals)) if inter_arrivals else 0.0
            inter_arrival_std = float(np.std(inter_arrivals)) if len(inter_arrivals) > 1 else 0.0
            
            # Transaction / Address Features
            addr_count = len(stats["addresses"])
            address_to_tx_ratio = addr_count / stats["tx_count"] if stats["tx_count"] > 0 else 1.0
            amount_concentration = stats["max_amount"] / stats["total_amount"] if stats["total_amount"] > 0 else 0.0

            base_feats = {
                "tx_count": float(stats["tx_count"]),
                "total_amount": float(stats["total_amount"]),
                "avg_amount": float(np.mean(amounts)) if amounts else 0.0,
                "amount_variance": float(np.var(amounts)) if len(amounts) > 1 else 0.0,
                "amount_concentration": float(amount_concentration),
                "dst_ip_diversity": float(len(stats["dst_ips"])),
                "port_diversity": float(len(stats["dst_ports"])),
                "address_reuse_count": float(addr_count),
                "address_to_tx_ratio": float(address_to_tx_ratio),
                "tx_velocity": float(tx_velocity),
                "inter_arrival_avg": inter_arrival_avg,
                "inter_arrival_std": inter_arrival_std
            }
            
            if self.graph:
                ip_node = f"IP:{ip}"
                if self.graph.has_node(ip_node):
                    base_feats["graph_degree"] = float(self.graph.degree(ip_node))
                    base_feats["fan_out"] = float(self.graph.out_degree(ip_node))
                    base_feats["fan_in"] = float(self.graph.in_degree(ip_node))
                    try:
                        ego = nx.ego_graph(self.graph, ip_node, radius=2)
                        base_feats["neighborhood_size"] = float(ego.number_of_nodes())
                    except Exception:
                        base_feats["neighborhood_size"] = float(base_feats["graph_degree"])
                else:
                    base_feats["graph_degree"] = 0.0
                    base_feats["fan_out"] = 0.0
                    base_feats["fan_in"] = 0.0
                    base_feats["neighborhood_size"] = 0.0
            
            self.entity_features[ip] = base_feats
            
        return self.entity_features
