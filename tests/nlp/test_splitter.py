from zeno.nlp.splitter import split_utterance

def test_single_intent():
    assert split_utterance("add a task") == ["add a task"]

def test_split_by_and():
    assert split_utterance("add a task and remind me later") == ["add a task", "remind me later"]

def test_split_by_then():
    assert split_utterance("start dev mode then open figma") == ["start dev mode", "open figma"]

def test_mixed_case():
    assert split_utterance("Add task AND then remind me") == ["Add task", "remind me"]

def test_empty_string():
    assert split_utterance("") == []
