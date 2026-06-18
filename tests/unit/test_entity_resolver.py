from app.graph.entity_resolver import resolve_entities


def test_resolves_local_plant_name():
    entities = resolve_entities("Apa kandungan jahe dan kunyit?")
    names = {x.canonical_name for x in entities}
    assert "Zingiber officinale" in names
    assert "Curcuma longa" in names
