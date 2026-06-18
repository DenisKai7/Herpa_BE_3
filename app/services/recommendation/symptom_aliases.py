SYMPTOM_ALIASES = {
    "batuk berdahak": [
        "batuk",
        "dahak",
        "ekspektoran",
        "mukolitik",
        "saluran pernapasan",
        "radang tenggorokan",
    ],
    "tenggorokan gatal": [
        "tenggorokan",
        "iritasi tenggorokan",
        "radang tenggorokan",
        "batuk",
        "antiinflamasi",
    ],
    "batuk": [
        "batuk",
        "ekspektoran",
        "saluran pernapasan",
    ],
    "pilek": [
        "pilek",
        "flu",
        "hidung tersumbat",
    ],
    "mual": [
        "mual",
        "antiemetik",
        "pencernaan",
    ],
    "perut kembung": [
        "kembung",
        "karminatif",
        "pencernaan",
    ],
}


def expand_symptoms(symptoms: list[str]) -> list[str]:
    expanded: set[str] = set()

    for symptom in symptoms:
        normalized = " ".join(symptom.strip().lower().split())
        if not normalized:
            continue

        expanded.add(normalized)

        for alias in SYMPTOM_ALIASES.get(normalized, []):
            expanded.add(alias.lower())

    return sorted(expanded)
