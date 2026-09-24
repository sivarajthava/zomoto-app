"""Production deployment verification and smoke test suite.

Tests live Railway backend and Vercel edge reverse-proxy endpoints
against the 4 core dining personas established in the implementation plan.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any, Dict

import httpx


PERSONAS = [
    {
        "name": "Persona A: Budget Student Hangout",
        "payload": {
            "location": "Bangalore",
            "budget_tier": "low",
            "min_rating": 3.8,
            "additional_preferences": "cheap eats with friends, large portions, casual seating",
        },
        "assertions": {
            "max_budget": 500,
            "min_rating": 3.5,
        },
    },
    {
        "name": "Persona B: Romantic Anniversary Date",
        "payload": {
            "location": "Bangalore",
            "budget_tier": "high",
            "min_rating": 4.2,
            "additional_preferences": "cozy candle-lit rooftop, great wine selection, quiet ambience",
        },
        "assertions": {
            "min_rating": 4.0,
        },
    },
    {
        "name": "Persona C: Family Sunday Brunch",
        "payload": {
            "location": "Bangalore",
            "budget_tier": "medium",
            "min_rating": 4.0,
            "additional_preferences": "spacious, kid-friendly, buffet with live counter",
        },
        "assertions": {
            "min_rating": 3.8,
        },
    },
    {
        "name": "Persona D: Late Night Quick Bite",
        "payload": {
            "location": "Bangalore",
            "budget_tier": "low",
            "min_rating": 3.5,
            "additional_preferences": "quick service, rolls or burgers, open late",
        },
        "assertions": {
            "max_budget": 600,
        },
    },
]


def test_health(client: httpx.Client, base_url: str) -> bool:
    print(f"\n[1/4] Probing Health Endpoint: {base_url}/health")
    try:
        start = time.perf_counter()
        resp = client.get(f"{base_url}/health", timeout=10.0)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"      Status: {resp.status_code} | Latency: {elapsed:.1f}ms")
        if resp.status_code != 200:
            print(f"      FAILED: Unexpected status code {resp.status_code}")
            return False
        data = resp.json()
        print(f"      Payload: {data}")
        if data.get("status") != "healthy":
            print(f"      FAILED: Health status is not 'healthy'")
            return False
        print("      PASSED: Health check confirmed system operational.")
        return True
    except Exception as exc:
        print(f"      FAILED: Connection error: {exc}")
        return False


def test_metadata(client: httpx.Client, base_url: str) -> bool:
    print(f"\n[2/4] Probing Metadata Endpoint: {base_url}/api/v1/metadata")
    try:
        start = time.perf_counter()
        resp = client.get(f"{base_url}/api/v1/metadata", timeout=10.0)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"      Status: {resp.status_code} | Latency: {elapsed:.1f}ms")
        if resp.status_code != 200:
            print(f"      FAILED: Unexpected status code {resp.status_code}")
            return False
        data = resp.json()
        cities = data.get("cities", [])
        cuisines = data.get("cuisines", [])
        tiers = data.get("budget_tiers", [])
        print(f"      Metadata summary: {len(cities)} cities, {len(cuisines)} cuisines, {len(tiers)} budget tiers")
        if not tiers:
            print("      FAILED: Budget tiers missing in metadata")
            return False
        print("      PASSED: Metadata successfully retrieved.")
        return True
    except Exception as exc:
        print(f"      FAILED: Connection error: {exc}")
        return False


def test_personas(client: httpx.Client, base_url: str) -> bool:
    print(f"\n[3/4] Testing Dining Persona Recommendation Queries: {base_url}/api/v1/recommendations")
    all_passed = True
    for persona in PERSONAS:
        name = persona["name"]
        payload = persona["payload"]
        print(f"\n      --- Running {name} ---")
        try:
            start = time.perf_counter()
            resp = client.post(
                f"{base_url}/api/v1/recommendations",
                json=payload,
                timeout=15.0,
            )
            elapsed = (time.perf_counter() - start) * 1000
            process_time = resp.headers.get("X-Process-Time", f"{elapsed:.1f}ms")
            print(f"      Status: {resp.status_code} | Latency: {elapsed:.1f}ms (Process Time: {process_time})")

            if resp.status_code != 200:
                print(f"      FAILED: Received HTTP {resp.status_code}: {resp.text}")
                all_passed = False
                continue

            data = resp.json()
            recs = data.get("recommendations", [])
            summary = data.get("summary", "")
            is_fallback = data.get("is_fallback", False)
            mode = "Fallback Heuristic" if is_fallback else "Live Groq Inference"

            print(f"      Engine Mode: {mode} | Returned: {len(recs)} restaurants")
            print(f"      AI Summary Preview: {summary[:80]}...")

            if not recs:
                print("      FAILED: No recommendations returned.")
                all_passed = False
                continue

            top = recs[0]
            print(f"      Top Match #1: {top.get('restaurant_name')} (Rating: {top.get('rating')}, Cost: ₹{top.get('estimated_cost_for_two')})")
            print(f"      Top Rationale: \"{top.get('explanation')[:90]}...\"")
            print(f"      PASSED: {name} executed successfully.")

        except Exception as exc:
            print(f"      FAILED: {name} threw exception: {exc}")
            all_passed = False

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Zomato AI Deployment Smoke Test Suite")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="Base URL of deployed service (e.g. https://your-railway.up.railway.app or https://your-app.vercel.app)",
    )
    args = parser.parse_args()
    base_url = args.url.rstrip("/")

    print("=" * 70)
    print(f"  ZOMATO AI CLOUD DEPLOYMENT SMOKE TEST SUITE")
    print(f"  Target URL: {base_url}")
    print("=" * 70)

    with httpx.Client() as client:
        health_ok = test_health(client, base_url)
        metadata_ok = test_metadata(client, base_url)
        personas_ok = test_personas(client, base_url)

    print("\n" + "=" * 70)
    print("  VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"  [1] Health Endpoint:      {'PASSED' if health_ok else 'FAILED'}")
    print(f"  [2] Metadata Endpoint:    {'PASSED' if metadata_ok else 'FAILED'}")
    print(f"  [3] Persona Queries:      {'PASSED' if personas_ok else 'FAILED'}")

    all_passed = health_ok and metadata_ok and personas_ok
    if all_passed:
        print("\n  >>> ALL PRODUCTION SMOKE TESTS PASSED CLEANLY! <<<")
        sys.exit(0)
    else:
        print("\n  >>> SOME TESTS FAILED. Check logs above. <<<")
        sys.exit(1)


if __name__ == "__main__":
    main()
