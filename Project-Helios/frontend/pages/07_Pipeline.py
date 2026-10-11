import streamlit as st

st.set_page_config(page_title="Pipeline Architecture - Investigation Platform", layout="wide")

st.title("PIPELINE ARCHITECTURE")
st.markdown("##### Technical Architecture State")
st.markdown("---")

stages = [
    {
        "name": "DATA INGESTION",
        "purpose": "Load raw observations from source systems.",
        "input": "CSV / JSON Logs",
        "output": "Standardized DataFrames",
        "technology": "Pandas",
        "status": "COMPLETED"
    },
    {
        "name": "SCHEMA VALIDATION",
        "purpose": "Ensure data conforms to expected analytical types.",
        "input": "Standardized DataFrames",
        "output": "Validated DataFrames",
        "technology": "Pydantic",
        "status": "COMPLETED"
    },
    {
        "name": "NORMALIZATION",
        "purpose": "Clean and normalize identifiers (IPs, TxIDs).",
        "input": "Validated DataFrames",
        "output": "Normalized DataFrames",
        "technology": "Pandas",
        "status": "COMPLETED"
    },
    {
        "name": "CROSS-RECORD LINKAGE",
        "purpose": "Identify relationships between disparate records.",
        "input": "Normalized DataFrames",
        "output": "Edge Lists",
        "technology": "Pandas / Custom Logic",
        "status": "COMPLETED"
    },
    {
        "name": "GRAPH CONSTRUCTION",
        "purpose": "Build the topological representation of entities.",
        "input": "Edge Lists",
        "output": "GraphML",
        "technology": "NetworkX",
        "status": "COMPLETED"
    },
    {
        "name": "FEATURE ENGINEERING",
        "purpose": "Extract behavioral and structural metrics.",
        "input": "GraphML",
        "output": "Entity Feature Matrix",
        "technology": "NetworkX / Scipy",
        "status": "COMPLETED"
    },
    {
        "name": "ANOMALY DETECTION",
        "purpose": "Identify statistically unusual entities.",
        "input": "Entity Feature Matrix",
        "output": "Anomaly Scores",
        "technology": "scikit-learn / Isolation Forest",
        "status": "COMPLETED"
    },
    {
        "name": "BEHAVIORAL CLUSTERING",
        "purpose": "Group entities with similar behavioral profiles.",
        "input": "Entity Feature Matrix",
        "output": "Cluster IDs",
        "technology": "scikit-learn / DBSCAN",
        "status": "COMPLETED"
    },
    {
        "name": "EVIDENCE SYNTHESIS",
        "purpose": "Correlate ML outputs with supporting data.",
        "input": "Scores, Clusters, Features",
        "output": "Rich Alert Objects",
        "technology": "Custom Rules Engine",
        "status": "COMPLETED"
    },
    {
        "name": "RANKED ALERTS",
        "purpose": "Prioritize targets for analyst review.",
        "input": "Rich Alert Objects",
        "output": "latest_alerts.json",
        "technology": "Scoring Heuristics",
        "status": "COMPLETED"
    },
    {
        "name": "INVESTIGATION",
        "purpose": "Present actionable intelligence to analysts.",
        "input": "JSON / GraphML",
        "output": "Interactive UI",
        "technology": "Streamlit",
        "status": "ACTIVE"
    }
]

for stage in stages:
    with st.expander(f"**{stage['name']}** - Status: {stage['status']}", expanded=(stage['status'] == "ACTIVE")):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Purpose:** {stage['purpose']}")
            st.markdown(f"**Technology:** `{stage['technology']}`")
        with col2:
            st.markdown(f"**Input:** `{stage['input']}`")
            st.markdown(f"**Output:** `{stage['output']}`")
