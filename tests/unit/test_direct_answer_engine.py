import pytest

from app.core.constants import Persona
from app.services.ai.direct_answer_engine import build_direct_answer
from app.services.ai.query_intent import QueryIntent


@pytest.mark.asyncio
async def test_fast_medium_compound_list_skips_llm():
    result = await build_direct_answer(
        query="senyawa di dalam kelor apa aja?",
        intent=QueryIntent.COMPOUND_LIST,
        persona=Persona.UMUM,
        graph_context=_context(),
    )
    assert result.handled is True
    assert result.compound_count >= 3


@pytest.mark.asyncio
async def test_fast_medium_direct_answer_low_context():
    result = await build_direct_answer(query="senyawa kelor", intent=QueryIntent.COMPOUND_LIST, persona=Persona.UMUM, graph_context={"herb": {}})
    assert result.handled is False
    assert "tanaman" in result.warnings[0].lower()


@pytest.mark.asyncio
async def test_fast_medium_umum_hides_iupac():
    result = await build_direct_answer(query="senyawa kelor", intent=QueryIntent.COMPOUND_LIST, persona=Persona.UMUM, graph_context=_context())
    assert "2-(3,4-dihydroxyphenyl)" not in result.answer
    assert "Quercetin" in result.answer


@pytest.mark.asyncio
async def test_fast_medium_does_not_mix_nutrients():
    result = await build_direct_answer(query="senyawa aktif kelor", intent=QueryIntent.COMPOUND_LIST, persona=Persona.UMUM, graph_context=_context())
    answer = result.answer or ""
    assert "Kalsium" not in answer.split("Selain fitokimia")[0]
    assert "komponen nutrisi" in answer


@pytest.mark.asyncio
async def test_sources_must_be_grounded():
    result = await build_direct_answer(query="senyawa kelor", intent=QueryIntent.COMPOUND_LIST, persona=Persona.UMUM, graph_context=_context())
    assert result.sources[0].title == "Farmakope Herbal Indonesia"


@pytest.mark.asyncio
async def test_generic_journal_names_are_not_invented():
    result = await build_direct_answer(query="senyawa kelor", intent=QueryIntent.COMPOUND_LIST, persona=Persona.UMUM, graph_context=_context())
    assert "Journal of Ethnopharmacology" not in (result.answer or "")
    assert "Food Chemistry" not in (result.answer or "")


@pytest.mark.asyncio
async def test_data_insufficient_message_is_specific():
    result = await build_direct_answer(
        query="manfaat kelor",
        intent=QueryIntent.THERAPEUTIC_USE_LIST,
        persona=Persona.UMUM,
        graph_context={"herb": {"common_name": "kelor"}, "sources": []},
    )
    assert result.handled is False
    assert any("kegunaan terapeutik" in item for item in result.warnings)


def _context():
    return {
        "herb": {"common_name": "kelor", "scientific_name": "Moringa oleifera"},
        "compounds": [
            {"name": "Quercetin", "pubchemCID": "5280343", "iupac": "2-(3,4-dihydroxyphenyl)-3,5,7-trihydroxy-4H-chromen-4-one", "compoundClass": "flavonoid"},
            {"name": "2-(3,4-dihydroxyphenyl)-3,5,7-trihydroxy-4H-chromen-4-one", "pubchemCID": "5280343"},
            {"name": "Kaempferol", "compoundClass": "flavonoid"},
            {"name": "Asam klorogenat", "compoundClass": "asam fenolat"},
            {"name": "Glukosinolat", "compoundClass": "glukosinolat"},
            {"name": "Saponin", "compoundClass": "saponin"},
            {"name": "Kalsium", "compoundClass": "mineral"},
        ],
        "sources": [{"name": "Farmakope Herbal Indonesia", "source_type": "neo4j"}],
    }
