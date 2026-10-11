# SIH26146 - Intelligence Backend MVP

## Overview
This is the offline, batch-oriented, AI-powered network-blockchain intelligence backend for Project Helios (SIH26146). It ingests network/blockchain metadata, models entity behaviors via a multi-layered feature space, and leverages unsupervised ML to detect, cluster, and explain suspicious cryptocurrency scenarios.

### IMPORTANT: DATASET LIMITATION
**The official SIH synthetic dataset was not available in the development environment.**
Therefore, this repository relies on a **Controlled Validation Fixture**. The synthetic scenario dataset is used exclusively to validate the analytical pipeline's logic and does not represent official SIH results. 
Do not refer to this dataset as the official/production dataset.

## Architecture
```text
DATASET -> INGESTION & NORMALIZATION -> GRAPH CONSTRUCTION 
    -> FEATURE ENGINEERING (16 dimensions) 
    -> ISOLATION FOREST (Anomaly) + DBSCAN (Behavioral Clustering) 
    -> SCENARIO VALIDATION 
    -> EVIDENCE AGGREGATION 
    -> RANKED ALERTS
```

## Dataset Generation & Scenario Definitions
The `generate_fixture.py` creates explicit populations mimicking real-world and suspicious behaviors with ground-truth mapping:
* **Normal Behavior**: Occasional transactions, varied addresses, reasonable amounts.
* **SCN-001 (High Velocity)**: Massive transaction volume over seconds.
* **SCN-002 (High Fan-Out)**: Small transaction volume spreading out to hundreds of unique addresses/IPs.
* **SCN-003 (Address Reuse)**: Extensive transactions repeatedly reusing the exact same minimal address pool.
* **SCN-004 (Multi-IP Sybil)**: Multiple distinct IPs coordinating to interact with the exact same tiny destination footprint.
* **SCN-005 (Amount/Graph Outliers)**: Massive fiat-equivalent transfer bursts and looping graph edges.

## Feature Groups (16 dimensions)
The pipeline maps behavior to robust statistical features:
* **Temporal**: `tx_velocity`, `inter_arrival_avg`, `inter_arrival_std` (Detects burstiness).
* **Network**: `dst_ip_diversity`, `port_diversity` (Detects sweeps).
* **Transaction**: `tx_count`, `total_amount`, `avg_amount`, `amount_variance`, `amount_concentration` (Detects structuring).
* **Address**: `address_reuse_count`, `address_to_tx_ratio` (Detects strict reuse patterns).
* **Graph Topology**: `graph_degree`, `fan_in`, `fan_out`, `neighborhood_size` (Topological features computed via NetworkX).

## ML Methodology
* **Anomaly Detection**: `sklearn.ensemble.IsolationForest`
  * Contamination is strictly defaulted to `0.26` via CLI (`--contamination 0.26`) exclusively to capture the planted synthetic scenarios. This must be recalibrated for real datasets.
* **Behavioral Clustering**: `sklearn.cluster.DBSCAN`
  * Important: DBSCAN groups entities with similar feature vectors (Behavioral Populations). It is *not* Entity Resolution. A "Cluster" does not prove that two IPs are the same physical person; it simply means they act in identically suspicious ways.

## Graph & Linkage Methodology
The graph serves to explicitly maintain data-backed relationships (`IP -> OBSERVED -> TX -> CONTAINS -> ADDRESS`), allowing evidence-backed entity resolution prior to any behavioral inferences.

## Alert Ranking & Explainability
Alerts prioritize entities based on the **Investigation Confidence Score**. 
* **Note:** Confidence represents the strength of the available analytical evidence for prioritization. It is *not* a statistically calibrated "probability of malicious activity/guilt".
* **Explainability:** Evidence is generated dynamically based on feature percentiles (e.g. "Transaction velocity in 90th percentile"). We do not use hardcoded evidence rules, nor do we falsely claim this represents SHAP attribution.

## Evaluation Methodology (Controlled Validation)
A ground-truth validation layer operates post-inference on the development fixture to calculate Recall across the planted scenarios. This verifies the mathematical viability of the pipeline without manual tweaking.

## Limitations & Official Dataset Transition Plan
* **GeoIP**: Offline placeholder available; pending local database integration.
* **Sybil Detection**: Single-entity tabular anomaly detection inherently struggles with distributed Sybil actions. Over 80% is still caught via behavioral crossover, but explicit Community Detection algorithms could be added in a production scenario.
* **Transition Plan**: The ingestion parsers (`CSV`, `JSON`, `XML`) are strictly canonical. When the official SIH dataset drops, it will be seamlessly ingested with malformed rows automatically quarantined via `DataParser`.

## Execution (Offline Linux/Windows execution)
1. Generate the deterministic synthetic fixture:
```bash
python generate_fixture.py
```
2. Execute the detection pipeline offline:
```bash
python backend/app/main.py --input backend/data/raw/dev_fixture.csv --contamination 0.26
```
