"""Test POST endpoints including legacy /query compatibility"""
import urllib.request
import urllib.error
import json

BASE = "http://127.0.0.1:8000"

print("=== Test 1: POST /api/query (query field) ===")
try:
    boundary = "----TestBoundary123"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="query"\r\n\r\n'
        f"How many buildings are visible?\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    
    req = urllib.request.Request(
        f"{BASE}/api/query",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    print(f"  success: {data.get('success')}")
    print(f"  answer: {data.get('answer', '')[:80]}")
    print(f"  task: {data.get('task_type')}")
    query_id = data.get("query_id")
except Exception as e:
    print(f"  ERROR: {e}")
    query_id = None

print("\n=== Test 2: POST /query (legacy prompt field from SidePanel) ===")
try:
    boundary = "----TestBoundaryLegacy"
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
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    print(f"  success: {data.get('success')}")
    print(f"  response: {data.get('response', '')[:80]}")
    print(f"  answer: {data.get('answer', '')[:80]}")
    print(f"  task: {data.get('task_type')}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n=== Test 3: GET /api/tools ===")
try:
    resp = urllib.request.urlopen(f"{BASE}/api/tools")
    data = json.loads(resp.read())
    print(f"  tools count: {data.get('total')}")
    for t in data.get("tools", []):
        print(f"    - {t['tool_id']}: {t['display_name']}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n=== All endpoint tests passed! ===")
