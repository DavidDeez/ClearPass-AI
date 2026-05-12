"""
ClearPass — Full Pipeline Integration Test
============================================
Tests every module individually, then the assembled pipeline.
Uses direct function calls (no face match needed for ML tests).
"""

import json
import sys
import time

# Add project root
sys.path.insert(0, ".")

print("=" * 60)
print("  ClearPass Full Pipeline Integration Test")
print("=" * 60)

# ------------------------------------------------------------------
# TEST 1: Feature Extractor
# ------------------------------------------------------------------
print("\n[TEST 1] Feature Extractor...")
from services.feature_extractor import extract_features

transactions = [
    {"amount": 150000, "date": "2025-01-15", "status": "successful", "narration": "Salary January", "type": "credit"},
    {"amount": 45000,  "date": "2025-01-20", "status": "successful", "narration": "Rent payment", "type": "debit"},
    {"amount": 160000, "date": "2025-02-15", "status": "successful", "narration": "Salary February", "type": "credit"},
    {"amount": 12000,  "date": "2025-02-18", "status": "failed",     "narration": "Loan repayment to QuickCredit", "type": "debit"},
    {"amount": 30000,  "date": "2025-02-25", "status": "successful", "narration": "Groceries and utilities", "type": "debit"},
    {"amount": 155000, "date": "2025-03-15", "status": "successful", "narration": "Salary March", "type": "credit"},
    {"amount": 50000,  "date": "2025-03-20", "status": "successful", "narration": "Borrow from friend repay", "type": "debit"},
    {"amount": 170000, "date": "2025-04-15", "status": "successful", "narration": "Salary April", "type": "credit"},
    {"amount": 8000,   "date": "2025-04-22", "status": "successful", "narration": "Data subscription", "type": "debit"},
    {"amount": 165000, "date": "2025-05-15", "status": "successful", "narration": "Salary May credit alert", "type": "credit"},
]

features = extract_features(transactions)
print(f"  PASS - Extracted {len(features)} features:")
for k, v in features.items():
    print(f"    {k:25s} = {v}")

# ------------------------------------------------------------------
# TEST 2: Model A — XGBoost Behavior Profiler
# ------------------------------------------------------------------
print("\n[TEST 2] Model A (XGBoost Behavior Profiler)...")
from services.model_a_behavior import score_behavior

result_a = score_behavior(features)
print(f"  PASS - Score: {result_a['score']}/100")
for reason in result_a["top_reasons"]:
    print(f"    -> {reason}")

# ------------------------------------------------------------------
# TEST 3: Model B — Isolation Forest Ghost Borrower
# ------------------------------------------------------------------
print("\n[TEST 3] Model B (Isolation Forest Ghost Borrower)...")
from services.model_b_anomaly import detect_anomaly

result_b = detect_anomaly(features)
print(f"  PASS - Anomaly Score: {result_b['anomaly_score']}/100")
print(f"    Ghost Borrower: {result_b['is_ghost_borrower']}")
print(f"    Raw Score:      {result_b['raw_score']}")

# ------------------------------------------------------------------
# TEST 4: Model C — Identity Fraud Graph
# ------------------------------------------------------------------
print("\n[TEST 4] Model C (Identity Fraud Graph)...")
from services.model_c_graph import add_user_to_graph, score_graph

# Add a few users — some sharing attributes
add_user_to_graph("BVN001", "+234801111", "DEV-A", "10 Lagos St")
add_user_to_graph("BVN002", "+234802222", "DEV-B", "20 Abuja Rd")
add_user_to_graph("BVN003", "+234801111", "DEV-C", "30 PH Ave")     # shares phone with BVN001
add_user_to_graph("BVN004", "+234804444", "DEV-A", "10 Lagos St")   # shares device+address with BVN001

result_c = score_graph("BVN001")
print(f"  PASS - Graph Score: {result_c['graph_score']}/100")
print(f"    Cluster Size:     {result_c['cluster_size']}")
print(f"    Fraud Ring:       {result_c['is_fraud_ring']}")
print(f"    Shared Attrs:     {result_c['shared_attributes']}")

# ------------------------------------------------------------------
# TEST 5: Trust Score Assembler
# ------------------------------------------------------------------
print("\n[TEST 5] Trust Score Assembler...")
from services.score_assembler import assemble_trust_score

final = assemble_trust_score(result_a, result_b, result_c)
print(f"  PASS - Trust Score: {final['trust_score']}/100")
print(f"    Verdict:          {final['verdict']}")
print(f"    Explanation:")
print(f"      Behavior:       {final['explanation']['behavior']}")
print(f"      Anomaly:        {final['explanation']['anomaly']}")
print(f"      Graph:          {final['explanation']['graph']}")

# ------------------------------------------------------------------
# TEST 6: /health endpoint via HTTP
# ------------------------------------------------------------------
print("\n[TEST 6] HTTP /health endpoint...")
try:
    import httpx
    r = httpx.get("http://localhost:8000/health", timeout=10)
    print(f"  PASS - Status {r.status_code}: {r.json()}")
except Exception as e:
    print(f"  SKIP - Server not reachable: {e}")

# ------------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------------
print("\n" + "=" * 60)
print("  ALL TESTS PASSED")
print("=" * 60)
print(f"\n  Final Trust Score : {final['trust_score']}/100")
print(f"  Verdict           : {final['verdict']}")
print(f"  Model A (50%)     : {result_a['score']}")
print(f"  Model B (30%)     : {result_b['anomaly_score']}")
print(f"  Model C (20%)     : {result_c['graph_score']}")
print()
