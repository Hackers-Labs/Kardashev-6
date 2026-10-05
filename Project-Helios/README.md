# Project Helios / SIH26146 - Intelligence Platform

## 1. Project Purpose
This is the offline, batch-oriented, AI-powered network-blockchain intelligence platform for SIH26146. It ingests network/blockchain metadata, models entity behaviors via a multi-layered feature space, leverages unsupervised ML to detect and cluster suspicious entities, and exposes this through a dedicated investigation console UI.

## 2. Architecture
```text
DATASET -> INGESTION & NORMALIZATION -> GRAPH CONSTRUCTION 
    -> FEATURE ENGINEERING (16 dimensions) 
    -> ISOLATION FOREST (Anomaly) + DBSCAN (Clustering) 
    -> EVIDENCE AGGREGATION -> RANKED ALERTS
    -> STREAMLIT INVESTIGATION CONSOLE
```

## 3. Backend Pipeline
The backend executes a full data lifecycle: parsing raw fixture data (CSV), generating topological GraphML representations using NetworkX, extracting 16 robust analytical features (temporal, network, amount, and structural), and emitting strictly schema-validated JSON artifacts for consumption by the frontend.

## 4. ML Methodology
* **Anomaly Detection (Isolation Forest)**: Chosen because it operates offline, scales efficiently, handles multi-dimensional interactions natively, and performs well unsupervised.
  * *Note on Contamination Parameter*: The current IsolationForest `contamination` is statically configured at 0.26 to closely reflect the proportion of intentionally planted anomalies (~25%) in the synthetic development fixture. This parameter will need dynamic tuning when transitioning to real SIH data.
* **Explainability**: Alert ranking uses an Investigation Confidence score based on heuristic evidence weighting, not a calibrated probability of maliciousness. Evidence reasons expose actual decile comparisons against the dataset population.

## 5. Behavioral Clustering
**DBSCAN** is utilized to segment the population based on behavioral profiles across the feature space, isolating distinct behavioral clusters from general noise. Note: These are explicitly labeled as *Behavioral Clusters*, not strict entity resolution.

## 6. Scenario Validation
A ground-truth validation layer operates post-inference to calculate **Recall** across planted scenarios (e.g., HIGH_VELOCITY, ADDRESS_REUSE) to mathematically verify system logic. Note: This represents controlled synthetic scenario recovery, not real-world production accuracy.

## 7. Frontend Investigation Console
A Streamlit multi-page application consuming the backend artifacts. It features an Alert Queue, Investigation Case files exposing explicitly calculated evidence, a Network Graph workspace (using depth-limited subgraph extraction), an Entity Explorer, and Pipeline visibility.

## 8. Offline Operation
The entire platform is 100% offline-first. It does not rely on external APIs, CDN JavaScript, Google Fonts, remote graph assets, or internet telemetry. Graph visualization relies on local `networkx` and `matplotlib` static rendering.

## 9. Installation
Requires Python 3.9+.
```bash
pip install pandas scikit-learn networkx pydantic streamlit matplotlib
```

## 10. Backend Execution
To execute the pipeline from a clean state:
```bash
python generate_fixture.py
python backend/app/main.py --input backend/data/raw/dev_fixture.csv
```

## 11. Frontend Execution
To start the investigation UI:
```bash
cd frontend
streamlit run app.py
```
*(Or use `run_frontend.bat` on Windows).*

## 12. Demonstration Flow
1. **Overview**: View system metrics, detection summary, and pipeline health.
2. **Alert Queue**: View ranked investigation targets.
3. **Investigation**: Select a high-priority alert and view trace evidence (Why Flagged, Behavioral, Graph, Linkage, ML Interpretation).
4. **Network Graph**: Expand an investigated entity to 1 or 2 hops and view its structural context statically.
5. **Entity Explorer**: Search entity metadata and direct relationships.
6. **Behavioral Clusters**: View DBSCAN population analysis.
7. **Validation & Pipeline**: Review architecture mappings and ground-truth recovery metrics.

## 13. Current Limitations
* Static Matplotlib rendering of subgraphs (intentional tradeoff for 100% offline reliability).
* Contamination threshold is hardcoded to synthetic injection rates for development.
* Scale is tested for ~3k-5k records locally in single-batch execution.

## 14. Synthetic Dataset Disclaimer
**DEVELOPMENT VALIDATION ONLY**
The official SIH synthetic dataset was not available in this environment. The platform is running on a **Controlled Synthetic Validation Dataset**. All entities, transactions, and addresses are fabricated to validate analytical logic. This system is architecturally ready for official data but must not be presented as having analyzed real SIH data.
