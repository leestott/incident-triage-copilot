"""E2E test script for the Incident Triage Copilot."""
import json
import sys

import httpx

BASE = "http://127.0.0.1:8080"


def main():
    passed = 0
    failed = 0

    # Test 1: Health check
    r = httpx.get(f"{BASE}/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    print(f"[PASS] Health: {data}")
    passed += 1

    # Test 2: Root serves HTML UI
    r = httpx.get(BASE, follow_redirects=True)
    assert r.status_code == 200
    ct = r.headers.get("content-type", "")
    assert "text/html" in ct, f"Expected HTML, got {ct}"
    assert "Incident Triage Copilot" in r.text
    print(f"[PASS] Root serves UI HTML ({len(r.text)} bytes)")
    passed += 1

    # Test 3: Static CSS
    r = httpx.get(f"{BASE}/static/css/style.css")
    assert r.status_code == 200
    print(f"[PASS] Static CSS ({len(r.text)} bytes)")
    passed += 1

    # Test 4: Static JS
    r = httpx.get(f"{BASE}/static/js/app.js")
    assert r.status_code == 200
    print(f"[PASS] Static JS ({len(r.text)} bytes)")
    passed += 1

    # Test 5: Triage - basic query
    r = httpx.post(
        f"{BASE}/triage",
        json={"message": "API response times spiked to 5s with 503 errors"},
        timeout=30,
    )
    assert r.status_code == 200
    data = r.json()
    assert "correlation_id" in data
    assert len(data["results"]) > 0
    agents = data["specialists_invoked"]
    print(f"[PASS] Triage basic: agents={agents}, turns={data['turn_count']}")
    print(f"       Summary: {data['summary'][:150]}...")
    passed += 1

    # Test 6: Triage with context
    r = httpx.post(
        f"{BASE}/triage",
        json={
            "message": "OOM kills happening on pods",
            "context": {"log_data": "ERROR 2026-03-20 OOM killed process 1234"},
        },
        timeout=30,
    )
    assert r.status_code == 200
    data = r.json()
    assert "diagnostics" in data["specialists_invoked"]
    print(f"[PASS] Triage+context: agents={data['specialists_invoked']}")
    passed += 1

    # Test 7: Triage with remediation query
    r = httpx.post(
        f"{BASE}/triage",
        json={"message": "How do I rollback the last deployment and fix the issue?"},
        timeout=30,
    )
    assert r.status_code == 200
    data = r.json()
    assert "remediation" in data["specialists_invoked"]
    print(f"[PASS] Triage+remediation: agents={data['specialists_invoked']}")
    passed += 1

    # Test 8: Validation error
    r = httpx.post(f"{BASE}/triage", json={"message": ""})
    assert r.status_code == 422
    print("[PASS] Validation: empty message returns 422")
    passed += 1

    # Test 9: API docs available
    r = httpx.get(f"{BASE}/docs")
    assert r.status_code == 200
    print("[PASS] Swagger docs available at /docs")
    passed += 1

    print(f"\n{'='*50}")
    print(f"E2E Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
