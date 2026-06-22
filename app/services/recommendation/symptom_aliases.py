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
    "panas dalam": [
        "panas dalam",
        "tenggorokan panas",
        "mulut terasa panas",
        "iritasi tenggorokan",
        "radang mulut",
        "sariawan",
    ],
    "sariawan": [
        "sariawan",
        "luka mulut",
        "stomatitis",
        "ulkus mulut",
        "radang mulut",
    ],
    "demam": [
        "demam",
        "badan panas",
        "suhu tinggi",
        "antipiretik",
    ],
    "maag": [
        "maag",
        "sakit lambung",
        "asam lambung",
        "perut perih",
        "pencernaan",
    ],
    "diare": [
        "diare",
        "mencret",
        "buang air besar cair",
        "pencernaan",
    ],
    "sakit kepala": [
        "sakit kepala",
        "pusing",
        "migrain",
        "sefalgia",
    ],
    "masuk angin": [
        "masuk angin",
        "flu",
        "pilek",
        "badan pegal",
        "kembung",
    ],
    "sakit gigi": [
        "sakit gigi",
        "nyeri gigi",
        "gigi berlubang",
        "radang gusi",
    ],
    "insomnia": [
        "insomnia",
        "susah tidur",
        "gangguan tidur",
        "sedatif",
    ],
    "radang tenggorokan": [
        "radang tenggorokan",
        "sakit tenggorokan",
        "faringitis",
        "tenggorokan",
        "antiinflamasi",
    ],
    "luka": [
        "luka",
        "luka bakar",
        "antiseptik",
        "penyembuhan luka",
    ],
    "tekanan darah tinggi": [
        "tekanan darah tinggi",
        "hipertensi",
        "darah tinggi",
        "antihipertensi",
    ],
    "diabetes": [
        "diabetes",
        "gula darah tinggi",
        "kencing manis",
        "antidiabetes",
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
