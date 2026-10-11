import streamlit as st
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_loader import load_graph, get_alert_by_entity

st.set_page_config(page_title="Entity Explorer - Investigation Platform", layout="wide")

st.title("ENTITY EXPLORER")
st.markdown("##### Universal investigation search")
st.markdown("---")

graph = load_graph()

if not graph:
    st.warning("Graph data is not available.")
    st.stop()

search_query = st.text_input("Search IP, Transaction ID, or Address")

if search_query:
    search_query = search_query.strip()
    
    if search_query in graph:
        node_data = graph.nodes[search_query]
        node_type = node_data.get('type', 'UNKNOWN')
        
        st.markdown(f"### IDENTITY: `{search_query}`")
        st.markdown(f"**Type:** `{node_type}`")
        
        # Determine network relationships
        neighbors = list(graph.neighbors(search_query))
        degree = len(neighbors)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### NETWORK RELATIONSHIPS")
            st.metric("Direct Connections (Degree)", degree)
            
            st.markdown("**Sample Connections:**")
            for neighbor in neighbors[:10]:
                neighbor_type = graph.nodes[neighbor].get('type', 'UNKNOWN')
                st.code(f"{neighbor_type}: {neighbor}")
            if degree > 10:
                st.markdown(f"...and {degree - 10} more.")
                
        with col2:
            st.markdown("#### ALERT HISTORY")
            if node_type == 'IP':
                alert = get_alert_by_entity(search_query)
                if alert:
                    st.error(f"⚠️ Active Alert: {alert['alert_id']}")
                    st.markdown(f"**Confidence:** {alert['confidence']:.4f}")
                    st.markdown(f"**Anomaly Score:** {alert['anomaly_score']:.4f}")
                    st.markdown(f"**Cluster:** {alert['cluster_id'] if alert['cluster_id'] != -1 else 'NOISE'}")
                    st.markdown("**Reasons:**")
                    for reason in alert['reasons']:
                        st.markdown(f"- {reason}")
                else:
                    st.success("✅ No active alerts for this IP.")
            else:
                st.info("Alert history is primarily tracked at the IP entity level.")
    else:
        st.error("Entity not found in the current dataset.")
