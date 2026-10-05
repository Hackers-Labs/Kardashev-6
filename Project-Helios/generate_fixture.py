import csv
import json
import random
from datetime import datetime, timedelta
import os

def generate_fixture(filepath, ground_truth_path):
    random.seed(42)
    start_time = datetime(2026, 10, 1, 12, 0, 0)
    
    ips = [f"192.168.1.{i}" for i in range(1, 201)]
    addresses = [f"1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa_{i}" for i in range(1000)]
    
    records = []
    ground_truth = {}
    tx_counter = 0
    
    def add_record(src_ip, ts, tx_addrs, tx_amounts, dst_ip=None):
        nonlocal tx_counter
        tx_counter += 1
        records.append({
            "timestamp": ts.isoformat(),
            "src_ip": src_ip,
            "dst_ip": dst_ip if dst_ip else random.choice(ips),
            "src_port": random.randint(1024, 65535),
            "dst_port": 8333,
            "txid": f"tx_{tx_counter:05d}",
            "addresses": ";".join(tx_addrs),
            "amounts": ";".join(map(lambda x: f"{x:.4f}", tx_amounts))
        })

    current_time = start_time
    
    # --- POPULATION A: Normal Behavior (IPs 1 to 150) ---
    # Occasional transactions, varied addresses, reasonable amounts
    for ip in ips[0:150]:
        num_txs = random.randint(1, 10)
        # Add normal overlapping noise: occasionally a normal user does 20 txs
        if random.random() < 0.05: num_txs = random.randint(15, 30)
        
        for _ in range(num_txs):
            current_time += timedelta(minutes=random.randint(10, 120))
            tx_addrs = random.sample(addresses, random.randint(1, 3))
            tx_amts = [random.uniform(0.01, 2.5) for _ in tx_addrs]
            add_record(ip, current_time, tx_addrs, tx_amts)

    # --- POPULATION B: High-Velocity (SCN-001) (IPs 151-160) ---
    # Massive number of transactions in a very short time window
    for ip in ips[150:160]:
        ground_truth[ip] = {"scenario_id": "SCN-001", "scenario_type": "HIGH_VELOCITY", "expected": "DETECT"}
        t = current_time + timedelta(hours=random.randint(1, 24))
        for _ in range(random.randint(80, 150)):
            t += timedelta(seconds=random.randint(1, 5))
            tx_addrs = random.sample(addresses, 1)
            add_record(ip, t, tx_addrs, [random.uniform(0.1, 0.5)])

    # --- POPULATION C: High-Fan-Out / Broad Network (SCN-002) (IPs 161-170) ---
    # Few transactions, but sending to massive numbers of addresses / unique IPs
    for ip in ips[160:170]:
        ground_truth[ip] = {"scenario_id": "SCN-002", "scenario_type": "HIGH_FAN_OUT", "expected": "DETECT"}
        t = current_time + timedelta(hours=random.randint(1, 24))
        for _ in range(random.randint(1, 3)):
            t += timedelta(minutes=random.randint(10, 60))
            tx_addrs = random.sample(addresses, random.randint(40, 80))
            tx_amts = [random.uniform(0.01, 0.1) for _ in tx_addrs]
            add_record(ip, t, tx_addrs, tx_amts)

    # --- POPULATION D: Address Reuse Patterns (SCN-003) (IPs 171-180) ---
    # High number of transactions, but exclusively reusing the exact same 1-2 addresses
    for ip in ips[170:180]:
        ground_truth[ip] = {"scenario_id": "SCN-003", "scenario_type": "ADDRESS_REUSE", "expected": "DETECT"}
        t = current_time + timedelta(hours=random.randint(1, 24))
        reused_addrs = random.sample(addresses, 2)
        for _ in range(random.randint(40, 60)):
            t += timedelta(minutes=random.randint(5, 30))
            add_record(ip, t, reused_addrs, [random.uniform(1.0, 5.0), random.uniform(1.0, 5.0)])

    # --- POPULATION E: Multi-IP Association (SCN-004) (IPs 181-190) ---
    # Multiple distinct IPs interacting with the exact same tiny cluster of destination IPs and addresses
    target_dst_ip = "192.168.99.99"
    target_addrs = random.sample(addresses, 3)
    for ip in ips[180:190]:
        ground_truth[ip] = {"scenario_id": "SCN-004", "scenario_type": "MULTI_IP_SYBIL", "expected": "DETECT"}
        t = current_time + timedelta(hours=random.randint(1, 24))
        for _ in range(random.randint(60, 90)):
            t += timedelta(minutes=random.randint(2, 5))
            add_record(ip, t, target_addrs, [random.uniform(0.5, 1.5) for _ in target_addrs], dst_ip=target_dst_ip)

    # --- POPULATION F: Graph & Amount Outliers (SCN-005) (IPs 191-200) ---
    # Massive amounts, weird graphing (sending to self or closed loop, huge volume)
    for ip in ips[190:200]:
        ground_truth[ip] = {"scenario_id": "SCN-005", "scenario_type": "AMOUNT_GRAPH_OUTLIER", "expected": "DETECT"}
        t = current_time + timedelta(hours=random.randint(1, 24))
        for _ in range(random.randint(2, 5)):
            t += timedelta(minutes=random.randint(30, 120))
            tx_addrs = random.sample(addresses, random.randint(2, 5))
            # Massive amounts
            tx_amts = [random.uniform(10000.0, 50000.0) for _ in tx_addrs]
            add_record(ip, t, tx_addrs, tx_amts)

    # Shuffle and sort by time
    random.shuffle(records)
    records.sort(key=lambda x: x["timestamp"])
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "src_ip", "dst_ip", "src_port", "dst_port", "txid", "addresses", "amounts"])
        writer.writeheader()
        writer.writerows(records)

    with open(ground_truth_path, 'w') as f:
        json.dump(ground_truth, f, indent=2)

if __name__ == "__main__":
    generate_fixture("backend/data/raw/dev_fixture.csv", "backend/data/raw/ground_truth.json")
    print("Generated controlled scenario development fixture and ground truth.")
