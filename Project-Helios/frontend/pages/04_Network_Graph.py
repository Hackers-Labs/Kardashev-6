import streamlit as st
import os
import sys
import networkx as nx
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_loader import load_graph, load_latest_alerts

st.set_page_config(page_title="Network Graph - Investigation Platform", layout="wide")

st.title("NETWORK GRAPH WORKSPACE")
st.markdown("---")

graph = load_graph()
alerts_data = load_latest_alerts()

if not graph:
    st.warning("Graph data is not available.")
    st.stop()

col1, col2 = st.columns([1, 3])

with col1:
    st.markdown("#### GRAPH CONTROLS")
    
    # Extract IPs for selection
    if alerts_data:
        ip_options = [a['entity_id'] for a in alerts_data['alerts']]
    else:
        # Fallback to random nodes if no alerts
        ip_options = [n for n, d in graph.nodes(data=True) if d.get('type') == 'IP'][:100]
        
    selected_node = st.selectbox("Selected Entity (IP)", ["None"] + ip_options)
    depth = st.radio("Depth", [1, 2], index=0, horizontal=True)
    
    st.markdown("**Node Types**")
    show_ip = st.checkbox("IP", value=True)
    show_tx = st.checkbox("Transaction", value=True)
    show_addr = st.checkbox("Address", value=True)
    
    st.markdown("**Edge Types**")
    show_observed = st.checkbox("OBSERVED", value=True)
    show_contains = st.checkbox("CONTAINS", value=True)

with col2:
    st.markdown("#### INVESTIGATION WORKSPACE")
    if selected_node == "None":
        st.info("Select an entity from the controls to begin structural analysis.")
    else:
        if selected_node in graph:
            # Subgraph extraction
            nodes_to_include = {selected_node}
            current_layer = {selected_node}
            
            for _ in range(depth):
                next_layer = set()
                for n in current_layer:
                    if n in graph:
                        next_layer.update(graph.neighbors(n))
                nodes_to_include.update(next_layer)
                current_layer = next_layer
                
            subgraph = graph.subgraph(nodes_to_include).copy()
            
            # Apply node type filters
            nodes_to_remove = []
            for n, d in subgraph.nodes(data=True):
                ntype = d.get('type', '')
                if ntype == 'IP' and not show_ip: nodes_to_remove.append(n)
                if ntype == 'TX' and not show_tx: nodes_to_remove.append(n)
                if ntype == 'ADDRESS' and not show_addr: nodes_to_remove.append(n)
            subgraph.remove_nodes_from(nodes_to_remove)
            
            # Apply edge type filters
            edges_to_remove = []
            for u, v, d in subgraph.edges(data=True):
                etype = d.get('type', '')
                if etype == 'OBSERVED' and not show_observed: edges_to_remove.append((u, v))
                if etype == 'CONTAINS' and not show_contains: edges_to_remove.append((u, v))
            subgraph.remove_edges_from(edges_to_remove)
            
            if len(subgraph.nodes) > 1000:
                st.warning(f"Subgraph is too large ({len(subgraph.nodes)} nodes). Please reduce depth or filter types.")
            else:
                # Render using matplotlib
                fig, ax = plt.subplots(figsize=(10, 8))
                
                # Colors based on node type
                colors = []
                sizes = []
                for n, d in subgraph.nodes(data=True):
                    ntype = d.get('type', '')
                    if n == selected_node:
                        colors.append('red')
                        sizes.append(300)
                    elif ntype == 'IP':
                        colors.append('lightblue')
                        sizes.append(100)
                    elif ntype == 'TX':
                        colors.append('lightgreen')
                        sizes.append(50)
                    elif ntype == 'ADDRESS':
                        colors.append('orange')
                        sizes.append(75)
                    else:
                        colors.append('gray')
                        sizes.append(50)
                
                pos = nx.spring_layout(subgraph, seed=42)
                nx.draw(subgraph, pos, with_labels=False, node_color=colors, node_size=sizes, ax=ax, alpha=0.7)
                
                # Highlight selected node label
                if selected_node in pos:
                    ax.text(pos[selected_node][0], pos[selected_node][1]+0.05, s=selected_node, 
                            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'),
                            horizontalalignment='center')
                
                st.pyplot(fig)
                
                st.markdown("#### DETAIL PANEL")
                st.markdown(f"**Node ID:** `{selected_node}`")
                st.markdown(f"**Node Type:** `IP`")
                st.markdown(f"**Neighborhood Size (rendered):** {len(subgraph.nodes)} nodes, {len(subgraph.edges)} edges")
                st.info("Visualization limited to selected neighborhood.")
        else:
            st.error(f"Node {selected_node} not found in the graph.")
