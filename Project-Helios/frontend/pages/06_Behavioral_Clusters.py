import streamlit as st
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_loader import load_latest_alerts

st.set_page_config(page_title="Behavioral Clusters - Investigation Platform", layout="wide")

st.title("BEHAVIORAL CLUSTERS")
st.markdown("##### Unsupervised population analysis")
st.info("The current DBSCAN output represents BEHAVIORAL CLUSTERS. It is NOT automatically entity resolution.")
st.markdown("---")

alerts_data = load_latest_alerts()

if not alerts_data:
    st.warning("No alerts data available.")
    st.stop()

# Group by cluster
clusters = {}
for alert in alerts_data['alerts']:
    c_id = alert.get('cluster_id', -1)
    if c_id not in clusters:
        clusters[c_id] = []
    clusters[c_id].append(alert)

# Display Cluster List
st.markdown("#### IDENTIFIED POPULATIONS")

for c_id, members in sorted(clusters.items()):
    if c_id == -1:
        cluster_name = "NOISE / NOT ASSIGNED"
        border_color = "rgba(128, 128, 128, 0.5)"
    else:
        cluster_name = f"Cluster {c_id}"
        border_color = "rgba(0, 128, 255, 0.5)"
        
    with st.container():
        st.markdown(f"<div style='border: 1px solid {border_color}; padding: 15px; margin-bottom: 15px; border-radius: 5px;'>", unsafe_allow_html=True)
        st.markdown(f"**{cluster_name}**")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Population Size", len(members))
        
        # Calculate avg anomaly score
        avg_score = sum(m['anomaly_score'] for m in members) / len(members)
        c2.metric("Avg Anomaly Score", f"{avg_score:.4f}")
        
        # Find representative reasons
        reasons = {}
        for m in members:
            for r in m.get('reasons', []):
                reasons[r] = reasons.get(r, 0) + 1
        
        top_reason = sorted(reasons.items(), key=lambda x: x[1], reverse=True)[0][0] if reasons else "N/A"
        c3.metric("Dominant Behavior", top_reason.split('(')[0].strip() if top_reason != "N/A" else "Mixed")
        
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("#### POPULATION DETAILS")
selected_cluster = st.selectbox("Select Cluster to inspect members", ["NOISE / NOT ASSIGNED"] + [f"Cluster {c}" for c in clusters.keys() if c != -1])

if selected_cluster == "NOISE / NOT ASSIGNED":
    inspect_id = -1
else:
    inspect_id = int(selected_cluster.replace("Cluster ", ""))

inspect_members = clusters.get(inspect_id, [])
table_data = []
for m in inspect_members:
    table_data.append({
        "ENTITY ID": m['entity_id'],
        "ANOMALY SCORE": f"{m['anomaly_score']:.4f}",
        "PRIMARY SIGNAL": m['reasons'][0] if m.get('reasons') else "N/A"
    })

st.dataframe(table_data, use_container_width=True)
