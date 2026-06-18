from app.graph.compound_normalizer import CompoundNormalizer


def test_compound_dedupe_by_pubchem():
    compounds = CompoundNormalizer.deduplicate(
        [
            {"name": "Quercetin", "pubchemCID": "5280343"},
            {"name": "2-(3,4-dihydroxyphenyl)-3,5,7-trihydroxy-4H-chromen-4-one", "pubchemCID": "5280343"},
        ],
        persona="umum",
    )
    assert len(compounds) == 1
    assert compounds[0]["name"] == "Quercetin"
    assert compounds[0]["iupac"] is None


def test_compound_dedupe_by_name():
    compounds = CompoundNormalizer.deduplicate(
        [
            {"name": "Asam klorogenat (3-5%)"},
            {"name": "asam-klorogenat"},
        ]
    )
    assert len(compounds) == 1


def test_compound_prioritize_active_before_nutrients():
    compounds = CompoundNormalizer.deduplicate(
        [
            {"name": "Kalsium", "compoundClass": "mineral"},
            {"name": "Quercetin", "compoundClass": "flavonoid"},
        ]
    )
    ordered = CompoundNormalizer.prioritize_active(compounds)
    assert ordered[0]["name"] == "Quercetin"
