import streamlit as st
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_loader import load_scenario_results, BACKEND_DIR

st.set_page_config(page_title="Validation - Investigation Platform", layout="wide")

st.title("MODEL VALIDATION")
st.markdown("##### Controlled scenario recovery — development validation")
st.markdown("---")

results = load_scenario_results()

if not results:
    st.info("NO VALIDATION RESULT AVAILABLE\n\nReason: The backend has not yet generated scenario evaluation output.")
else:
    st.markdown("### SCENARIO RECOVERY METRICS")
    
    table_data = []
    for scenario, data in results.items():
        table_data.append({
            "SCENARIO": scenario.replace("_", " "),
            "EXPECTED ENTITIES": data.get("planted", 0),
            "DETECTED": data.get("detected", 0),
            "RECALL": f"{data.get('recall', 0.0):.2f}",
            "STATUS": "✅ PASS" if data.get('recall', 0) >= 0.8 else "⚠️ REVIEW"
        })
        
    st.dataframe(table_data, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("### SYSTEM METADATA")
    st.markdown("**Validation Type:** CONTROLLED VALIDATION")
    st.markdown("**Dataset:** Synthetic controlled injection")
    
    # Load Run Metadata from demo_report if available
    demo_report_path = os.path.join(BACKEND_DIR, "demo_report.json")
    if os.path.exists(demo_report_path):
        try:
            with open(demo_report_path, 'r') as f:
                report = json.load(f)
                
            st.markdown("---")
            st.markdown("### RUN METADATA")
            st.json({
                "Timestamp": report.get("timestamp", "N/A"),
                "Records Processed": report.get("records_processed", "N/A"),
                "High Confidence Alerts": report.get("alerts_generated", {}).get("high_confidence", "N/A"),
                "Total Alerts": report.get("alerts_generated", {}).get("total", "N/A"),
                "Status": report.get("status", "N/A")
            })
        except:
            pass
