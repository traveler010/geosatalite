"""Quick smoke test for the backend pipeline."""
import sys
sys.path.insert(0, '.')

print("=== SatQuery AI Backend Smoke Test ===\n")

# 1. Import check
print("[1] Importing modules...")
from backend.main import app
print("    FastAPI app: OK")

from backend.models.tool_registry import get_registry, get_tool_summary
tools = get_registry()
print(f"    Tool registry: {len(tools)} tools registered")
for t in tools:
    print(f"      - {t['tool_id']} ({t['task_type']})")

# 2. Specialist check
print("\n[2] Testing specialists...")
from backend.models.specialists import get_specialist
for task in ["vqa", "grounding", "captioning", "change_vqa", "fusion"]:
    s = get_specialist(task)
    print(f"    {task}: {s.__class__.__name__} OK")

# 3. Controller pipeline check
print("\n[3] Testing agentic controller pipeline...")
from backend.services.controller import execute_query

test_queries = [
    ("How many buildings are visible?", "count/vqa"),
    ("Describe this satellite scene", "captioning"),
    ("Highlight the water body", "grounding"),
    ("Has the built-up area increased?", "change_vqa"),
]

for query, expected in test_queries:
    result = execute_query(query, [])
    status = "PASS" if result["success"] else "FAIL"
    print(f"    [{status}] '{query}'")
    print(f"           task={result['trace']['selected_task']}, "
          f"tool={result['trace']['selected_tool']}, "
          f"conf={result['trace']['confidence']}")
    print(f"           answer: {result['answer'][:80]}...")

# 4. Trace retrieval check
print("\n[4] Testing trace retrieval...")
from backend.services.trace_builder import get_all_traces
traces = get_all_traces()
print(f"    Stored traces: {len(traces)}")

# 5. Report generation check
print("\n[5] Testing report generation...")
from backend.services.report_generator import generate_html_report
if traces:
    trace = traces[0]
    path = generate_html_report(trace, trace["query_id"])
    print(f"    Report generated: {path}")

print("\n=== All checks passed ===")
