import csv
import json
import xml.etree.ElementTree as ET
from dateutil.parser import parse as parse_date
from typing import List, Tuple
from backend.app.models import CanonicalRecord

class DataParser:
    def __init__(self):
        self.valid_records = 0
        self.invalid_records = 0
        self.quarantined = []
        
    def _parse_timestamp(self, ts_str):
        try:
            return parse_date(ts_str)
        except Exception:
            return None

    def _parse_list_str(self, val, sep=";"):
        if not val: return []
        return [x.strip() for x in str(val).split(sep) if x.strip()]

    def _parse_list_float(self, val, sep=";"):
        if not val: return []
        try:
            return [float(x.strip()) for x in str(val).split(sep) if x.strip()]
        except ValueError:
            return []

    def _validate_and_normalize(self, row) -> CanonicalRecord:
        try:
            timestamp = self._parse_timestamp(row.get('timestamp'))
            src_ip = row.get('src_ip', '').strip()
            dst_ip = row.get('dst_ip', '').strip()
            
            try:
                src_port = int(row.get('src_port', 0))
                dst_port = int(row.get('dst_port', 0))
            except ValueError:
                src_port, dst_port = 0, 0
                
            txid = row.get('txid', '').strip()
            
            # Use semi-colon delimiter for addresses and amounts for now, 
            # or JSON list if it comes as a list natively
            addrs = row.get('addresses')
            amts = row.get('amounts')
            
            if isinstance(addrs, str):
                addresses = self._parse_list_str(addrs)
            elif isinstance(addrs, list):
                addresses = [str(x) for x in addrs]
            else:
                addresses = []
                
            if isinstance(amts, str):
                amounts = self._parse_list_float(amts)
            elif isinstance(amts, list):
                amounts = [float(x) for x in amts]
            else:
                amounts = []

            if not timestamp or not src_ip or not txid:
                raise ValueError("Missing critical fields")

            return CanonicalRecord(
                timestamp=timestamp,
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_port=src_port,
                dst_port=dst_port,
                txid=txid,
                addresses=addresses,
                amounts=amounts,
                raw_data=row
            )
        except Exception as e:
            raise ValueError(f"Validation failed: {str(e)}")

    def load_csv(self, path: str) -> List[CanonicalRecord]:
        records = []
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    record = self._validate_and_normalize(row)
                    records.append(record)
                    self.valid_records += 1
                except ValueError as e:
                    self.invalid_records += 1
                    self.quarantined.append({"row": row, "error": str(e)})
        return records

    def load_json(self, path: str) -> List[CanonicalRecord]:
        records = []
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = [data]
            for row in data:
                try:
                    record = self._validate_and_normalize(row)
                    records.append(record)
                    self.valid_records += 1
                except ValueError as e:
                    self.invalid_records += 1
                    self.quarantined.append({"row": row, "error": str(e)})
        return records

    def load_xml(self, path: str) -> List[CanonicalRecord]:
        records = []
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            for child in root:
                row = {subchild.tag: subchild.text for subchild in child}
                try:
                    record = self._validate_and_normalize(row)
                    records.append(record)
                    self.valid_records += 1
                except ValueError as e:
                    self.invalid_records += 1
                    self.quarantined.append({"row": row, "error": str(e)})
        except Exception as e:
            print(f"Failed to parse XML: {e}")
        return records

    def load_dataset(self, path: str) -> List[CanonicalRecord]:
        if path.endswith('.csv'):
            return self.load_csv(path)
        elif path.endswith('.json'):
            return self.load_json(path)
        elif path.endswith('.xml'):
            return self.load_xml(path)
        else:
            raise ValueError("Unsupported file format")

    def summary(self):
        return {
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "quarantined_count": len(self.quarantined)
        }
