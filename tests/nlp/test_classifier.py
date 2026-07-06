from zeno.nlp.classifier import get_classifier

def test_classifier_add_task():
    classifier = get_classifier()
    intent = classifier.classify("Add a task to fix the login bug")
    assert intent is not None
    assert intent.intent_category == "task_management"
    assert intent.intent_name == "add_task"
    assert intent.confidence >= 0.75

def test_classifier_query_schedule():
    classifier = get_classifier()
    intent = classifier.classify("What is my schedule for today?")
    assert intent is not None
    assert intent.intent_category == "day_planning"
    assert intent.intent_name == "query_schedule"

def test_classifier_low_confidence():
    classifier = get_classifier()
    # Something completely unrelated or gibberish
    intent = classifier.classify("supercalifragilisticexpialidocious")
    assert intent is None
