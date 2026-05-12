#!/usr/bin/env python3
"""
ClearPass — Test Script
========================
Sends a realistic test request to the /verify endpoint.
Run this after starting the server with: uvicorn main:app --reload

Usage:
    python test_verify.py
"""

import base64
import json
import os

import httpx

BASE_URL = os.environ.get("CLEARPASS_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Generate a tiny synthetic 8x8 red PNG as placeholder images.
# In production, these would be real base64 selfie / ID photos.
# ---------------------------------------------------------------------------
def _make_test_image_b64() -> str:
    """Create a minimal valid PNG image and return its base64 encoding."""
    from PIL import Image
    import io

    img = Image.new("RGB", (160, 160), color=(200, 160, 120))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def main():
    live_b64 = _make_test_image_b64()
    official_b64 = _make_test_image_b64()

    payload = {
        "bvn": "22345678901",
        "phone": "+2348012345678",
        "device_id": "DEVICE-ABC-123",
        "address": "15 Admiralty Way, Lekki, Lagos",
        "live_image_b64": live_b64,
        "official_image_b64": official_b64,
        "transactions": [
            {
                "amount": 150000.00,
                "date": "2025-01-15",
                "status": "successful",
                "narration": "Salary January",
                "type": "credit",
            },
            {
                "amount": 45000.00,
                "date": "2025-01-20",
                "status": "successful",
                "narration": "Rent payment",
                "type": "debit",
            },
            {
                "amount": 160000.00,
                "date": "2025-02-15",
                "status": "successful",
                "narration": "Salary February",
                "type": "credit",
            },
            {
                "amount": 12000.00,
                "date": "2025-02-18",
                "status": "failed",
                "narration": "Loan repayment to QuickCredit",
                "type": "debit",
            },
            {
                "amount": 30000.00,
                "date": "2025-02-25",
                "status": "successful",
                "narration": "Groceries and utilities",
                "type": "debit",
            },
            {
                "amount": 155000.00,
                "date": "2025-03-15",
                "status": "successful",
                "narration": "Salary March",
                "type": "credit",
            },
            {
                "amount": 50000.00,
                "date": "2025-03-20",
                "status": "successful",
                "narration": "Borrow from friend repay",
                "type": "debit",
            },
            {
                "amount": 170000.00,
                "date": "2025-04-15",
                "status": "successful",
                "narration": "Salary April",
                "type": "credit",
            },
            {
                "amount": 8000.00,
                "date": "2025-04-22",
                "status": "successful",
                "narration": "Data subscription",
                "type": "debit",
            },
            {
                "amount": 165000.00,
                "date": "2025-05-15",
                "status": "successful",
                "narration": "Salary May credit alert",
                "type": "credit",
            },
        ],
    }

    print("=" * 60)
    print("  ClearPass /verify Test")
    print("=" * 60)
    print(f"\nTarget: {BASE_URL}/verify")
    print(f"BVN:    {payload['bvn']}")
    print(f"Txns:   {len(payload['transactions'])} transactions\n")

    try:
        resp = httpx.post(
            f"{BASE_URL}/verify",
            json=payload,
            timeout=60.0,
        )
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))
    except httpx.ConnectError:
        print("ERROR: Could not connect. Is the server running?")
        print(f"  Start it with: uvicorn main:app --host 0.0.0.0 --port 8000")
    except Exception as exc:
        print(f"ERROR: {exc}")


if __name__ == "__main__":
    main()
