from app.services.ai.query_intent import QueryIntent, classify_query_intent, normalize_query_text


def test_compound_list_intent():
    assert classify_query_intent("senyawa di dalam kelor apa aja?") == QueryIntent.COMPOUND_LIST
    assert classify_query_intent("senyawa aktif temulawak") == QueryIntent.COMPOUND_LIST
    assert classify_query_intent("kandungan kimia kunyit") == QueryIntent.COMPOUND_LIST


def test_indonesian_informal_normalization():
    text = normalize_query_text("senyawa aktifnya di dalam kelor apa aja?")
    assert "senyawa aktif" in text
    assert "dalam" in text
    assert "apa saja" in text
