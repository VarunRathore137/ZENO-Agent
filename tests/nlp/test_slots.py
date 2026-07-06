import datetime
from zeno.nlp.slots import get_extractor

def test_extract_priority():
    extractor = get_extractor()
    assert extractor.extract_priority("urgent task") == "critical"
    assert extractor.extract_priority("high priority bug") == "high"
    assert extractor.extract_priority("minor fix") == "low"
    assert extractor.extract_priority("normal task") == "medium"

def test_extract_duration_minutes():
    extractor = get_extractor()
    assert extractor.extract_duration_minutes("for 2 hours") == 120
    assert extractor.extract_duration_minutes("take 45 minutes") == 45
    assert extractor.extract_duration_minutes("half an hour") == 30

def test_extract_date():
    extractor = get_extractor()
    today = datetime.date.today()
    assert extractor.extract_date("do this today") == today.isoformat()
    assert extractor.extract_date("due tomorrow") == (today + datetime.timedelta(days=1)).isoformat()

def test_extract_all_add_task():
    extractor = get_extractor()
    slots = extractor.extract_all("add task fix the login bug due tomorrow high priority", "add_task")
    assert slots["title"] == "fix the login bug"
    assert slots["priority"] == "high"
    assert "due_date" in slots
