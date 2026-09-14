"""
SatQuery AI — Comprehensive API Integration Test Suite
Tests all endpoints: Health, Root, Tools, Query, Legacy Query, Traces, Report, NASA APOD.
"""
import urllib.request
import urllib.error
import json
import time

BASE = "http://127.0.0.1:8000"

def run_tests():
    print("=" * 60)
    print("SatQuery AI — Full API Integration Suite")
    print("=" * 60)

    # 1. Health check
    print("\n[Test 1] GET /health")
    try:
        req = urllib.request.Request(f"{BASE}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            assert data.get("status") == "healthy"
            print("  Status: OK ->", data)
    except Exception as e:
        print("  Status: FAILED ->", e)

    # 2. Root check
    print("\n[Test 2] GET /")
    try:
        req = urllib.request.Request(f"{BASE}/")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            assert data.get("service") == "SatQuery AI"
            print(f"  Status: OK -> Service: {data.get('service')}, Version: {data.get('version')}")
    except Exception as e:
        print("  Status: FAILED ->", e)

    # 3. Tools Registry
    print("\n[Test 3] GET /api/tools")
    try:
        with urllib.request.urlopen(f"{BASE}/api/tools", timeout=5) as resp:
            data = json.loads(resp.read())
            total = data.get("total", 0)
            print(f"  Status: OK -> Total tools: {total}")
            for t in data.get("tools", []):
                print(f"    - [{t['task_type']}] {t['tool_id']}: {t['display_name']}")
    except Exception as e:
        print("  Status: FAILED ->", e)

    # 4. Tool Detail
    print("\n[Test 4] GET /api/tools/rs_vqa_v1")
    try:
        with urllib.request.urlopen(f"{BASE}/api/tools/rs_vqa_v1", timeout=5) as resp:
            data = json.loads(resp.read())
            print(f"  Status: OK -> Tool: {data.get('display_name')}, Tasks: {data.get('task_type')}")
    except Exception as e:
        print("  Status: FAILED ->", e)

    # 5. POST /api/query
    print("\n[Test 5] POST /api/query (V2 agentic pipeline)")
    query_id = None
    try:
        boundary = "----SatQueryTestBoundary123"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="query"\r\n\r\n'
            f"How many buildings are visible in this scene?\r\n"
            f"--{boundary}--\r\n"
        ).encode()

        req = urllib.request.Request(
            f"{BASE}/api/query",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            assert data.get("success") is True
            query_id = data.get("query_id")
            print(f"  Status: OK -> Query ID: {query_id}")
            print(f"  Task: {data.get('task_type')}, Tool: {data.get('tool_used')}")
            print(f"  Confidence: {data.get('confidence')}")
            print(f"  Answer: {data.get('answer', '')[:70]}...")
    except Exception as e:
        print("  Status: FAILED ->", e)

    # 6. POST /query (Legacy route from SidePanel)
    print("\n[Test 6] POST /query (Legacy frontend compatibility)")
    try:
        boundary = "----SatQueryLegacyBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="prompt"\r\n\r\n'
            f"Describe this satellite scene\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="location"\r\n\r\n'
            f'{{"latitude": 13.7199, "longitude": 80.2304, "altitude": 3000}}\r\n'
            f"--{boundary}--\r\n"
        ).encode()

        req = urllib.request.Request(
            f"{BASE}/query",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            assert data.get("success") is True
            assert "response" in data
            print(f"  Status: OK -> Task: {data.get('task_type')}")
            print(f"  Response: {data.get('response', '')[:70]}...")
    except Exception as e:
        print("  Status: FAILED ->", e)

    # 7. GET /api/traces
    print("\n[Test 7] GET /api/traces")
    try:
        with urllib.request.urlopen(f"{BASE}/api/traces", timeout=5) as resp:
            data = json.loads(resp.read())
            print(f"  Status: OK -> Total traces: {data.get('total')}")
    except Exception as e:
        print("  Status: FAILED ->", e)

    # 8. GET /api/trace/{query_id}
    if query_id:
        print(f"\n[Test 8] GET /api/trace/{query_id}")
        try:
            with urllib.request.urlopen(f"{BASE}/api/trace/{query_id}", timeout=5) as resp:
                data = json.loads(resp.read())
                print(f"  Status: OK -> Trace query: {data.get('query')}")
                print(f"  Task: {data.get('selected_task')}, Tool: {data.get('selected_tool')}")
        except Exception as e:
            print("  Status: FAILED ->", e)

    # 9. GET /api/report/{query_id}
    if query_id:
        print(f"\n[Test 9] GET /api/report/{query_id}")
        try:
            with urllib.request.urlopen(f"{BASE}/api/report/{query_id}", timeout=5) as resp:
                content_type = resp.headers.get("Content-Type", "")
                length = len(resp.read())
                print(f"  Status: OK -> Type: {content_type}, Length: {length} bytes")
        except Exception as e:
            print("  Status: FAILED ->", e)

    # 10. NASA APOD Feed
    print("\n[Test 10] GET /api/nasa/apod")
    try:
        with urllib.request.urlopen(f"{BASE}/api/nasa/apod?count=2", timeout=10) as resp:
            data = json.loads(resp.read())
            items = data.get("items", [])
            print(f"  Status: OK -> Success: {data.get('success')}, Items: {len(items)}")
            if items:
                print(f"    First item: {items[0].get('title')} ({items[0].get('date')})")
    except Exception as e:
        print("  Status: FAILED ->", e)

    print("\n" + "=" * 60)
    print("API Integration Suite Complete")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
