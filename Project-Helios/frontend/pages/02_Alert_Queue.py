import streamlit as st
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_loader import load_latest_alerts

st.set_page_config(page_title="Alert Queue - Investigation Platform", layout="wide")

st.title("ALERT QUEUE")
st.markdown("##### Ranked entities requiring analytical review")
st.markdown("---")

alerts_data = load_latest_alerts()

if not alerts_data:
    st.warning("No alerts data available.")
    st.stop()

# Filters
col1, col2, col3, col4 = st.columns(4)

with col1:
    search_query = st.text_input("Search IP / Alert ID")
with col2:
    min_confidence = st.slider("Min Investigation Confidence", 0.0, 1.0, 0.5)
with col3:
    clusters = sorted(list(set(a.get('cluster_id') for a in alerts_data['alerts'])))
    selected_cluster = st.selectbox("Cluster", ["ALL"] + clusters)
with col4:
    status_filter = st.selectbox("Status", ["NEW", "IN_PROGRESS", "CLOSED"])

# Apply Filters
filtered_alerts = []
for alert in alerts_data['alerts']:
    if search_query and search_query.lower() not in alert['entity_id'].lower() and search_query.lower() not in alert['alert_id'].lower():
        continue
    if alert['confidence'] < min_confidence:
        continue
    if selected_cluster != "ALL" and alert['cluster_id'] != selected_cluster:
        continue
    filtered_alerts.append(alert)

# Sort by confidence
filtered_alerts = sorted(filtered_alerts, key=lambda x: x['confidence'], reverse=True)

table_data = []
for idx, alert in enumerate(filtered_alerts):
    table_data.append({
        "PRIORITY": "CRITICAL" if alert['confidence'] > 0.9 else "HIGH" if alert['confidence'] > 0.75 else "MEDIUM",
        "ALERT ID": alert['alert_id'],
        "ENTITY": alert['entity_id'],
        "ANOMALY SCORE": f"{alert['anomaly_score']:.4f}",
        "INVESTIGATION CONFIDENCE": f"{alert['confidence']:.4f}",
        "BEHAVIORAL CLUSTER": alert['cluster_id'] if alert['cluster_id'] != -1 else "NOISE",
        "PRIMARY SIGNAL": alert['reasons'][0] if alert['reasons'] else "N/A",
        "STATUS": "NEW"
    })

if table_data:
    st.dataframe(table_data, use_container_width=True, hide_index=True)
else:
    st.info("No alerts match the current filters.")
