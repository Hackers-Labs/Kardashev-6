import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from typing import Dict, Any

class EntityClusterer:
    def __init__(self, eps=1.5, min_samples=3):
        self.model = DBSCAN(eps=eps, min_samples=min_samples)
        self.scaler = StandardScaler()
        
    def fit_predict(self, entity_features: Dict[str, Dict[str, float]]) -> Dict[str, int]:
        entities = list(entity_features.keys())
        if not entities:
            return {}
            
        feature_names = list(entity_features[entities[0]].keys())
        
        X = []
        for e in entities:
            X.append([entity_features[e][f] for f in feature_names])
            
        X = np.array(X)
        X_scaled = self.scaler.fit_transform(X)
        
        preds = self.model.fit_predict(X_scaled)
        
        results = {}
        for i, e in enumerate(entities):
            results[e] = int(preds[i])  # -1 means noise in DBSCAN
            
        return results
