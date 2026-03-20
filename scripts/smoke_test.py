#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# smoke_test.py — Smoke test that calls the triage endpoint with sample prompts
# ---------------------------------------------------------------------------
# Usage:
#   python scripts/smoke_test.py                    # defaults to localhost:8080
#   python scripts/smoke_test.py --url https://...  # test deployed endpoint
# ---------------------------------------------------------------------------
import argparse
import json
import sys
import urllib.error
import urllib.request

# Sample prompts that exercise different routing paths
SAMPLE_PROMPTS = [
    {
        "name": "Research only — simple query",
        "payload": {
            "message": "Our user dashboard is loading slowly for EU customers."
        },
        "expect_specialists": ["research"],
    },
    {
        "name": "Research + Diagnostics — error with logs",
        "payload": {
            "message": "Getting 503 errors on the /api/orders endpoint since 2pm.",
            "context": {
                "log_data": (
                    "2025-01-15T14:00:12Z ERROR ConnectionPool exhausted (max=100)\n"
                    "2025-01-15T14:00:13Z ERROR Timeout waiting for DB connection\n"
                    "2025-01-15T14:00:14Z ERROR HTTP 503 returned to client\n"
                    "2025-01-15T14:00:15Z WARN Circuit breaker OPEN for orders-db\n"
                )
            },
        },
        "expect_specialists": ["research", "diagnostics"],
    },
    {
        "name": "All specialists — full triage with remediation",
        "payload": {
            "message": (
                "Production is down! OOM errors in the payment service. "
                "Need a fix and rollback plan immediately."
            ),
            "context": {
                "log_data": (
                    "2025-01-15T10:00:00Z FATAL java.lang.OutOfMemoryError: Java heap space\n"
                    "2025-01-15T10:00:01Z ERROR Pod payment-svc-7b8f restarted (OOMKilled)\n"
                    "2025-01-15T10:00:02Z WARN HPA scaling to 5 replicas\n"
                )
            },
        },
        "expect_specialists": ["research", "diagnostics", "remediation"],
    },
    {
        "name": "Remediation focus — runbook request",
        "payload": {
            "message": "Create a runbook for handling Redis connection failures."
        },
        "expect_specialists": ["research"],  # "runbook" isn't a keyword but investigate/fix patterns may vary
    },
    {
        "name": "Custom correlation ID",
        "payload": {
            "message": "Investigate latency spike in the auth service.",
            "correlation_id": "smoke-test-custom-id",
        },
        "expect_specialists": ["research", "diagnostics"],
    },
]


def run_smoke_tests(base_url: str) -> bool:
    """Run all smoke tests and return True if all pass."""
    triage_url = f"{base_url.rstrip('/')}/triage"
    passed = 0
    failed = 0

    print(f"\n{'='*60}")
    print(f"  Smoke Test — {triage_url}")
    print(f"{'='*60}\n")

    # Check health first
    try:
        health_req = urllib.request.Request(f"{base_url.rstrip('/')}/health")
        with urllib.request.urlopen(health_req, timeout=10) as resp:
            health = json.loads(resp.read())
            print(f"  Health: {health['status']} (mode={health['mode']})\n")
    except Exception as e:
        print(f"  FAIL: Health check failed — {e}")
        print(f"  Is the server running at {base_url}?")
        return False

    for i, test in enumerate(SAMPLE_PROMPTS, 1):
        print(f"  [{i}/{len(SAMPLE_PROMPTS)}] {test['name']}")

        try:
            data = json.dumps(test["payload"]).encode("utf-8")
            req = urllib.request.Request(
                triage_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())

            # Validate response structure
            assert "correlation_id" in result, "Missing correlation_id"
            assert "summary" in result, "Missing summary"
            assert len(result["summary"]) > 0, "Empty summary"
            assert len(result["results"]) > 0, "No results"

            # Validate custom correlation ID if provided
            if "correlation_id" in test["payload"]:
                assert result["correlation_id"] == test["payload"]["correlation_id"], (
                    f"Correlation ID mismatch: {result['correlation_id']}"
                )

            print(f"    PASS — {len(result['results'])} specialist(s), "
                  f"correlation={result['correlation_id'][:20]}...")
            passed += 1

        except urllib.error.HTTPError as e:
            print(f"    FAIL — HTTP {e.code}: {e.reason}")
            failed += 1
        except AssertionError as e:
            print(f"    FAIL — {e}")
            failed += 1
        except Exception as e:
            print(f"    FAIL — {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*60}\n")

    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Smoke test for Incident Triage Copilot")
    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="Base URL of the agent endpoint (default: http://localhost:8080)",
    )
    args = parser.parse_args()

    success = run_smoke_tests(args.url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
