import streamlit as st
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_loader import load_latest_alerts, get_alert_by_entity

st.set_page_config(page_title="Investigation Case - Platform", layout="wide")

st.title("INVESTIGATION CASE")
st.markdown("---")

alerts_data = load_latest_alerts()
if not alerts_data:
    st.warning("No alerts data available.")
    st.stop()

# Select Alert to investigate
alert_options = {a['alert_id']: a['entity_id'] for a in alerts_data['alerts']}
col1, _ = st.columns([1, 2])
with col1:
    selected_alert_id = st.selectbox("Select Alert", list(alert_options.keys()), format_func=lambda x: f"{x} - {alert_options[x]}")

if selected_alert_id:
    # Find alert
    alert = next((a for a in alerts_data['alerts'] if a['alert_id'] == selected_alert_id), None)
    
    if alert:
        # CASE HEADER
        st.markdown(f"### ALERT {alert['alert_id']}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("ENTITY", alert['entity_id'])
        c2.metric("ANOMALY SCORE", f"{alert['anomaly_score']:.4f}")
        c3.metric("INVESTIGATION CONFIDENCE", f"{alert['confidence']:.4f}")
        c4.metric("BEHAVIORAL CLUSTER", f"Cluster {alert['cluster_id']}" if alert['cluster_id'] != -1 else "NOISE")
        
        st.markdown("---")
        
        # SECTION A: WHY FLAGGED
        st.markdown("#### SECTION A: WHY FLAGGED")
        for reason in alert['reasons']:
            st.markdown(f"- {reason}")
            
        st.markdown("---")
        
        # SECTION B: BEHAVIORAL EVIDENCE
        st.markdown("#### SECTION B: BEHAVIORAL EVIDENCE")
        features = alert.get('features', {})
        
        bc1, bc2, bc3, bc4 = st.columns(4)
        bc1.metric("Transaction Count", f"{features.get('tx_count', 0):.0f}")
        bc2.metric("Transaction Velocity", f"{features.get('tx_velocity', 0):.2f}")
        bc3.metric("Total Amount", f"{features.get('total_amount', 0):.4f}")
        bc4.metric("Average Amount", f"{features.get('avg_amount', 0):.4f}")
        
        bc5, bc6, bc7, bc8 = st.columns(4)
        bc5.metric("IP Diversity", f"{features.get('dst_ip_diversity', 0):.0f}")
        bc6.metric("Address Reuse Count", f"{features.get('address_reuse_count', 0):.0f}")
        bc7.metric("Amount Variance", f"{features.get('amount_variance', 0):.4f}")
        bc8.metric("Inter-Arrival Avg", f"{features.get('inter_arrival_avg', 0):.2f}")

        st.markdown("---")
        
        # SECTION C: GRAPH EVIDENCE
        st.markdown("#### SECTION C: GRAPH EVIDENCE")
        gc1, gc2, gc3, gc4 = st.columns(4)
        gc1.metric("Graph Degree", f"{features.get('graph_degree', 0):.0f}")
        gc2.metric("Fan-In", f"{features.get('fan_in', 0):.0f}")
        gc3.metric("Fan-Out", f"{features.get('fan_out', 0):.0f}")
        gc4.metric("Neighborhood Size", f"{features.get('neighborhood_size', 0):.0f}")
        
        st.markdown("---")
        
        # SECTION D: LINKAGE EVIDENCE
        st.markdown("#### SECTION D: LINKAGE EVIDENCE")
        st.markdown(f"**Entity:** `{alert['entity_id']}`")
        st.markdown("Observed Relationships Trace:")
        st.code(f"""
{alert['entity_id']} (IP) 
  ├── OBSERVED → {features.get('tx_count', 0):.0f} Transactions
  └── CONTAINS → {features.get('address_reuse_count', 0):.0f} Addresses (estimated distinct)
        """, language="text")
        
        st.markdown("---")
        
        # SECTION E: MODEL INTERPRETATION
        st.markdown("#### SECTION E: MODEL INTERPRETATION")
        st.markdown(f"**Model:** `{alert.get('model', 'Unknown')}`")
        st.markdown(f"**Anomaly score:** `{alert['anomaly_score']:.4f}`")
        st.markdown("**Detection basis:** behavioral + structural signals")
        st.info("The anomaly score indicates model-derived unusualness relative to the dataset, not a calibrated probability of malicious activity. Investigation confidence prioritizes entities based on heuristic evidence weighting.")
