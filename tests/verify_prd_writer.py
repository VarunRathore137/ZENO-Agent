import sys
sys.path.insert(0, '.')

from zeno.ai.prd_writer import _parse_tasks_json, _parse_tasks_checkbox

# Test JSON parser
t = _parse_tasks_json('[{"title": "Test task", "priority": "high"}]', 'test')
assert t[0]['title'] == 'Test task'
print(f"JSON parse OK: '{t[0]['title']}'")

# Test checkbox fallback
t2 = _parse_tasks_checkbox("- [ ] Do A\n- [ ] Do B", 'test')
assert len(t2) == 2
print(f"Checkbox parse OK: {len(t2)} tasks")

# Test resilience
t3 = _parse_tasks_json("{bad json}", 'test')
assert t3 == []
print("Malformed JSON fallback OK")

print("prd_writer verification PASSED")
