import numpy as np
from sklearn.ensemble import IsolationForest
from typing import Dict, Any

class AnomalyDetector:
    def __init__(self, contamination=0.1):
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.feature_names = []
        
    def fit_predict(self, entity_features: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, Any]]:
        entities = list(entity_features.keys())
        if not entities:
            return {}
            
        self.feature_names = list(entity_features[entities[0]].keys())
        
        X = []
        for e in entities:
            X.append([entity_features[e][f] for f in self.feature_names])
            
        X = np.array(X)
        
        # Fit and predict
        preds = self.model.fit_predict(X)
        scores = self.model.decision_function(X)
        
        # Normalize scores to 0-1 range for a "confidence score"
        # IsolationForest decision_function: lower (negative) is more anomalous
        # We want higher to be more anomalous.
        # So we negate and scale.
        min_score = np.min(scores)
        max_score = np.max(scores)
        
        if max_score > min_score:
            norm_scores = (scores - min_score) / (max_score - min_score)
            # Invert so 1.0 is most anomalous
            norm_scores = 1.0 - norm_scores
        else:
            norm_scores = np.zeros_like(scores)
            
        results = {}
        for i, e in enumerate(entities):
            is_anomaly = (preds[i] == -1)
            results[e] = {
                "is_anomaly": bool(is_anomaly),
                "anomaly_score": float(norm_scores[i]),
                "raw_score": float(scores[i])
            }
            
        return results
