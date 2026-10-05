from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class CanonicalRecord:
    timestamp: datetime
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    txid: str
    addresses: List[str] = field(default_factory=list)
    amounts: List[float] = field(default_factory=list)
    
    # Keep unknown metadata if needed
    raw_data: dict = field(default_factory=dict)
