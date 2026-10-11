import networkx as nx
from typing import List, Dict, Any
from backend.app.models import CanonicalRecord

class GraphBuilder:
    def __init__(self, records: List[CanonicalRecord]):
        self.records = records
        self.graph = nx.DiGraph() # Directed graph to capture IP -> TX -> Address flow

    def build(self) -> nx.DiGraph:
        for r in self.records:
            # Nodes
            # Ensure unique IDs for different node types just in case IP and TX have same string
            ip_node = f"IP:{r.src_ip}"
            tx_node = f"TX:{r.txid}"
            
            # IP Node
            if not self.graph.has_node(ip_node):
                self.graph.add_node(ip_node, type="IP", original_id=r.src_ip)
                
            # TX Node
            if not self.graph.has_node(tx_node):
                self.graph.add_node(tx_node, type="TX", original_id=r.txid, timestamp=r.timestamp.isoformat() if r.timestamp else "")
                
            # IP -> TX edge
            self.graph.add_edge(ip_node, tx_node, relation="OBSERVED")
            
            # Address nodes and edges
            for idx, addr in enumerate(r.addresses):
                addr_node = f"ADDR:{addr}"
                if not self.graph.has_node(addr_node):
                    self.graph.add_node(addr_node, type="ADDRESS", original_id=addr)
                
                amount = r.amounts[idx] if idx < len(r.amounts) else 0.0
                # TX -> Address edge
                self.graph.add_edge(tx_node, addr_node, relation="CONTAINS", amount=amount)

        return self.graph

    def get_summary(self) -> Dict[str, Any]:
        node_types = {"IP": 0, "TX": 0, "ADDRESS": 0}
        for n, data in self.graph.nodes(data=True):
            n_type = data.get("type", "UNKNOWN")
            if n_type in node_types:
                node_types[n_type] += 1
                
        edge_types = {"OBSERVED": 0, "CONTAINS": 0}
        for u, v, data in self.graph.edges(data=True):
            rel = data.get("relation", "UNKNOWN")
            if rel in edge_types:
                edge_types[rel] += 1
                
        # Top degree
        degrees = sorted(self.graph.degree(), key=lambda x: x[1], reverse=True)
        top_ips = [(n, d) for n, d in degrees if n.startswith("IP:")][:5]
        top_txs = [(n, d) for n, d in degrees if n.startswith("TX:")][:5]
        top_addrs = [(n, d) for n, d in degrees if n.startswith("ADDR:")][:5]
        
        return {
            "num_nodes": self.graph.number_of_nodes(),
            "num_edges": self.graph.number_of_edges(),
            "node_counts": node_types,
            "edge_counts": edge_types,
            "top_ips": [{"id": n.replace("IP:", ""), "degree": d} for n, d in top_ips],
            "top_txs": [{"id": n.replace("TX:", ""), "degree": d} for n, d in top_txs],
            "top_addrs": [{"id": n.replace("ADDR:", ""), "degree": d} for n, d in top_addrs]
        }
