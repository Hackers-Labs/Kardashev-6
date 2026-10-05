import streamlit as st
import os
import sys

# Ensure frontend path is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_loader import load_latest_alerts, load_graph_summary

st.set_page_config(page_title="Overview - Investigation Platform", layout="wide")

st.title("Analytical Command Center")

alerts_data = load_latest_alerts()
graph_summary = load_graph_summary()

if not alerts_data or not graph_summary:
    st.warning("Backend data is currently unavailable. Please check the backend pipeline.")
    st.stop()

st.markdown("### SYSTEM OVERVIEW")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Records Processed", f"{alerts_data['summary']['valid_records']:,}")
with col2:
    st.metric("Unique IPs", f"{graph_summary['node_counts'].get('IP', 0):,}")
with col3:
    st.metric("Unique Transactions", f"{graph_summary['node_counts'].get('TX', 0):,}")
with col4:
    st.metric("Unique Addresses", f"{graph_summary['node_counts'].get('ADDRESS', 0):,}")
with col5:
    st.metric("Graph Edges", f"{graph_summary['num_edges']:,}")


st.markdown("---")
st.markdown("### DETECTION SUMMARY")
col1, col2, col3, col4 = st.columns(4)

total_alerts = len(alerts_data['alerts'])
high_priority = sum(1 for a in alerts_data['alerts'] if a['confidence'] > 0.8)

# Calculate clusters (excluding -1)
clusters = set(a.get('cluster_id') for a in alerts_data['alerts'] if a.get('cluster_id', -1) != -1)
noise_entities = sum(1 for a in alerts_data['alerts'] if a.get('cluster_id', -1) == -1)

with col1:
    st.metric("Total Alerts", total_alerts)
with col2:
    st.metric("High-Priority Alerts", high_priority)
with col3:
    st.metric("Behavioral Clusters", len(clusters))
with col4:
    st.metric("Noise Entities (Unclustered)", noise_entities)

st.markdown("---")
st.markdown("### ANALYTICAL PIPELINE")
st.markdown("""
<div style='font-family: monospace; padding: 10px; background-color: rgba(128,128,128,0.1); border-radius: 4px; border: 1px solid rgba(128,128,128,0.3);'>
INGEST &nbsp;→&nbsp; NORMALIZE &nbsp;→&nbsp; LINK &nbsp;→&nbsp; GRAPH &nbsp;→&nbsp; FEATURES &nbsp;→&nbsp; ML &nbsp;→&nbsp; EVIDENCE &nbsp;→&nbsp; ALERTS<br>
<span style='color: #00aa00;'>[OK]</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color: #00aa00;'>[OK]</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color: #00aa00;'>[OK]</span> &nbsp;&nbsp;&nbsp;&nbsp;<span style='color: #00aa00;'>[OK]</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color: #00aa00;'>[OK]</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color: #00aa00;'>[OK]</span> &nbsp;&nbsp;&nbsp;<span style='color: #00aa00;'>[OK]</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color: #00aa00;'>[READY]</span>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("### TOP INVESTIGATION TARGETS")

top_alerts = sorted(alerts_data['alerts'], key=lambda x: x['confidence'], reverse=True)[:10]

table_data = []
for idx, alert in enumerate(top_alerts):
    table_data.append({
        "RANK": idx + 1,
        "ALERT ID": alert['alert_id'],
        "ENTITY": alert['entity_id'],
        "ANOMALY SCORE": f"{alert['anomaly_score']:.4f}",
        "INVESTIGATION CONFIDENCE": f"{alert['confidence']:.4f}",
        "CLUSTER": alert['cluster_id'] if alert['cluster_id'] != -1 else "NOISE",
        "PRIMARY SIGNAL": alert['reasons'][0] if alert['reasons'] else "N/A"
    })

st.dataframe(table_data, use_container_width=True, hide_index=True)
