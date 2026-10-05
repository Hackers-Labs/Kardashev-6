import streamlit as st
import os

st.set_page_config(
    page_title="Investigation Intelligence Platform",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for technical styling
st.markdown("""
<style>
    /* Technical typography */
    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Monospace for technical identifiers */
    .mono {
        font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
        font-size: 0.9em;
    }

    /* Environment indicator */
    .env-indicator {
        font-size: 0.75em;
        font-weight: 600;
        letter-spacing: 0.05em;
        padding: 4px 8px;
        background-color: rgba(255, 150, 0, 0.15);
        color: #ff9900;
        border: 1px solid rgba(255, 150, 0, 0.3);
        border-radius: 4px;
        display: inline-block;
        margin-bottom: 1rem;
    }
    
    /* Restrained cards */
    .metric-card {
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 1rem;
        border-radius: 4px;
        background-color: rgba(128, 128, 128, 0.05);
    }
    
    .metric-title {
        font-size: 0.8em;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #888;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 1.5em;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### SIH26146")
    st.markdown("Investigation Intelligence Platform")
    
    st.markdown("---")
    
    st.markdown("**Environment:**")
    st.markdown('<div class="env-indicator">DEVELOPMENT VALIDATION</div>', unsafe_allow_html=True)
    
    st.markdown("**Dataset:**")
    st.markdown("`dev_fixture.csv`")
    
    st.markdown("**Run:**")
    st.markdown("`LATEST`")
    
    st.markdown("**Status:**")
    st.markdown("🟢 PIPELINE READY")

    st.markdown("---")
    
st.title("Investigation Intelligence Platform")
st.markdown("Please select a module from the left navigation panel to begin your investigation.")

st.markdown("---")
st.markdown("### PLATFORM CAPABILITIES")
st.markdown("""
* **01 Overview:** Analytical Command Center
* **02 Alert Queue:** Ranked entities requiring analytical review
* **03 Investigation:** Case-level evidence inspection
* **04 Network Graph:** Multi-hop structural analysis
* **05 Entity Explorer:** Universal investigation search
* **06 Behavioral Clusters:** Unsupervised population analysis
* **07 Pipeline:** Technical architecture state
* **08 Validation:** Controlled scenario recovery metrics
""")
