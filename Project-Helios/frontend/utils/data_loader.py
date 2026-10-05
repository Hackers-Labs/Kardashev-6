import json
import os
import streamlit as st
import networkx as nx

BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backend", "outputs")

@st.cache_data(ttl="1h")
def load_latest_alerts():
    file_path = os.path.join(BACKEND_DIR, "latest_alerts.json")
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        return None

@st.cache_data(ttl="1h")
def load_graph_summary():
    file_path = os.path.join(BACKEND_DIR, "latest_graph_summary.json")
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        return None

@st.cache_resource(ttl="1h")
def load_graph():
    file_path = os.path.join(BACKEND_DIR, "latest_graph.graphml")
    if not os.path.exists(file_path):
        return None
    try:
        # Load the graph with NetworkX
        return nx.read_graphml(file_path)
    except Exception as e:
        return None

@st.cache_data(ttl="1h")
def load_scenario_results():
    file_path = os.path.join(BACKEND_DIR, "scenario_results.json")
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        return None

def get_alert_by_entity(entity_id):
    alerts_data = load_latest_alerts()
    if not alerts_data or "alerts" not in alerts_data:
        return None
    for alert in alerts_data["alerts"]:
        if str(alert.get("entity_id")) == str(entity_id):
            return alert
    return None
