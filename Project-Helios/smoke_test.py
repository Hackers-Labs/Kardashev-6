import os
import sys

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'frontend')))

from streamlit.testing.v1 import AppTest

pages = [
    "frontend/app.py",
    "frontend/pages/01_Overview.py",
    "frontend/pages/02_Alert_Queue.py",
    "frontend/pages/03_Investigation.py",
    "frontend/pages/04_Network_Graph.py",
    "frontend/pages/05_Entity_Explorer.py",
    "frontend/pages/06_Behavioral_Clusters.py",
    "frontend/pages/07_Pipeline.py",
    "frontend/pages/08_Validation.py"
]

print("Starting Streamlit AppTest Smoke Test...")

for page in pages:
    try:
        at = AppTest.from_file(page)
        at.run()
        if at.exception:
            print(f"FAIL: {page} encountered an exception:")
            print(at.exception)
        else:
            print(f"PASS: {page}")
    except Exception as e:
        print(f"ERROR running AppTest for {page}: {e}")
