from __future__ import annotations

from typing import Any

QUIZ_LEVEL_TYPES = {
    1: "multiple_choice",
    2: "matching",
    3: "true_false",
    4: "short_answer",
    5: "case_based",
}

TOPIC_TITLES = [
    "Struktur Atom",
    "Tabel Periodik",
    "Ikatan Kimia",
    "Stoikiometri",
    "Larutan",
    "Asam Basa",
    "Kesetimbangan Kimia",
    "Termokimia",
    "Kinetika Kimia",
    "Elektrokimia",
    "Kimia Organik Dasar",
    "Biomolekul",
    "Farmakokimia",
    "Fitokimia Herbal",
    "Toksikologi Dasar",
    "Analisis Senyawa Obat",
]

DETAILED_BANKS: dict[str, dict[int, list[dict[str, Any]]]] = {
    "tabel-periodik": {
        1: [
            {"prompt": "Unsur yang berada dalam satu golongan pada tabel periodik umumnya memiliki kesamaan pada...", "options": ["jumlah neutron", "jumlah kulit elektron", "jumlah elektron valensi", "massa atom relatif"], "answer": "C", "explanation": "Elektron valensi menentukan kemiripan sifat kimia unsur dalam satu golongan."},
            {"prompt": "Golongan 18 pada tabel periodik dikenal sebagai...", "options": ["logam alkali", "halogen", "gas mulia", "lantanida"], "answer": "C", "explanation": "Golongan 18 berisi gas mulia yang relatif stabil."},
            {"prompt": "Unsur Na berada pada golongan...", "options": ["1", "2", "17", "18"], "answer": "A", "explanation": "Natrium adalah logam alkali golongan 1."},
            {"prompt": "Dalam satu periode dari kiri ke kanan, jari-jari atom cenderung...", "options": ["membesar", "mengecil", "tetap", "acak"], "answer": "B", "explanation": "Muatan inti efektif meningkat sehingga jari-jari atom mengecil."},
            {"prompt": "Halogen berada pada golongan...", "options": ["1", "2", "17", "18"], "answer": "C", "explanation": "Halogen berada di golongan 17."},
        ],
        2: [
            {"prompt": "Cocokkan golongan unsur dengan posisinya.", "pairs": {"Logam alkali": "Golongan 1", "Logam alkali tanah": "Golongan 2", "Halogen": "Golongan 17", "Gas mulia": "Golongan 18", "Karbon": "Golongan 14"}, "explanation": "Golongan adalah kolom vertikal dalam tabel periodik."},
            {"prompt": "Cocokkan tren periodik.", "pairs": {"Jari-jari atom satu periode": "mengecil", "Energi ionisasi satu periode": "meningkat", "Keelektronegatifan satu periode": "meningkat", "Karakter logam satu periode": "menurun", "Kulit elektron satu periode": "sama"}, "explanation": "Tren periodik dipengaruhi muatan inti efektif."},
            {"prompt": "Cocokkan unsur dengan kelompoknya.", "pairs": {"Na": "logam alkali", "Mg": "alkali tanah", "Cl": "halogen", "Ne": "gas mulia", "Fe": "logam transisi"}, "explanation": "Klasifikasi unsur didasarkan pada posisi dan sifat kimia."},
            {"prompt": "Cocokkan istilah tabel periodik.", "pairs": {"Golongan": "kolom vertikal", "Periode": "baris horizontal", "Nomor atom": "jumlah proton", "Elektron valensi": "elektron kulit terluar", "Gas mulia": "stabil"}, "explanation": "Istilah dasar membantu membaca tabel periodik."},
            {"prompt": "Cocokkan blok unsur.", "pairs": {"Blok s": "golongan 1-2", "Blok p": "golongan 13-18", "Blok d": "transisi", "Blok f": "lantanida/aktinida", "He": "gas mulia"}, "explanation": "Blok berkaitan dengan orbital yang terisi elektron terakhir."},
        ],
        3: [
            {"prompt": "Unsur dalam satu periode memiliki jumlah kulit elektron utama yang sama.", "answer": True, "explanation": "Nomor periode menunjukkan jumlah kulit elektron utama."},
            {"prompt": "Halogen termasuk golongan 18.", "answer": False, "explanation": "Halogen berada pada golongan 17."},
            {"prompt": "Natrium cenderung melepas elektron valensi.", "answer": True, "explanation": "Na adalah logam alkali dengan satu elektron valensi."},
            {"prompt": "Gas mulia sangat reaktif karena kekurangan elektron valensi.", "answer": False, "explanation": "Gas mulia relatif stabil karena kulit valensinya penuh."},
            {"prompt": "Keelektronegatifan umumnya meningkat dari kiri ke kanan dalam satu periode.", "answer": True, "explanation": "Tarikan inti terhadap elektron ikatan meningkat."},
        ],
        4: [
            {"prompt": "Apa nama golongan unsur pada golongan 18?", "answer": "gas mulia", "accepted": ["noble gas", "gas noble"], "explanation": "Golongan 18 dikenal sebagai gas mulia."},
            {"prompt": "Apa istilah untuk elektron pada kulit terluar atom?", "answer": "elektron valensi", "accepted": ["valensi"], "explanation": "Elektron valensi terlibat dalam ikatan kimia."},
            {"prompt": "Apa nama golongan 17?", "answer": "halogen", "accepted": ["halogen"], "explanation": "Golongan 17 disebut halogen."},
            {"prompt": "Apa nama baris horizontal pada tabel periodik?", "answer": "periode", "accepted": ["perioda"], "explanation": "Baris horizontal disebut periode."},
            {"prompt": "Apa nama kolom vertikal pada tabel periodik?", "answer": "golongan", "accepted": ["group"], "explanation": "Kolom vertikal disebut golongan."},
        ],
        5: [
            {"prompt": "Seorang siswa membandingkan Na dan Cl. Na mudah melepas elektron, sedangkan Cl cenderung menerima elektron. Penjelasan paling tepat adalah...", "options": ["Na dan Cl berada pada golongan yang sama", "Na adalah logam alkali dan Cl adalah halogen", "Na memiliki massa atom lebih besar", "Cl tidak memiliki elektron valensi"], "answer": "B", "explanation": "Na sebagai logam alkali cenderung melepas elektron; Cl sebagai halogen cenderung menerima elektron."},
            {"prompt": "Unsur X berada di golongan 18. Dalam kondisi umum, unsur X cenderung...", "options": ["sangat mudah membentuk ion +1", "relatif stabil", "selalu menjadi halogen", "memiliki satu elektron valensi"], "answer": "B", "explanation": "Golongan 18 adalah gas mulia yang relatif stabil."},
            {"prompt": "Unsur Y satu periode dengan Mg tetapi berada lebih kanan. Jari-jari atom Y dibanding Mg cenderung...", "options": ["lebih besar", "lebih kecil", "sama persis", "tidak dapat diprediksi"], "answer": "B", "explanation": "Jari-jari atom mengecil dari kiri ke kanan dalam satu periode."},
            {"prompt": "Senyawa garam dapur terbentuk dari Na dan Cl karena...", "options": ["keduanya gas mulia", "Na melepas elektron dan Cl menerima elektron", "keduanya nonlogam", "Cl melepas elektron ke Na"], "answer": "B", "explanation": "Transfer elektron membentuk ion Na+ dan Cl-."},
            {"prompt": "Jika unsur memiliki 7 elektron valensi, unsur itu kemungkinan termasuk...", "options": ["alkali", "alkali tanah", "halogen", "gas mulia"], "answer": "C", "explanation": "Halogen memiliki 7 elektron valensi."},
        ],
    },
}

# Topik prioritas lain: konten spesifik tapi ringkas.
DETAILED_BANKS["struktur-atom"] = {
    1: [
        {"prompt": "Partikel subatom bermuatan positif adalah...", "options": ["proton", "neutron", "elektron", "isotop"], "answer": "A", "explanation": "Proton bermuatan positif."},
        {"prompt": "Nomor atom menunjukkan jumlah...", "options": ["neutron", "proton", "massa atom", "kulit"], "answer": "B", "explanation": "Nomor atom sama dengan jumlah proton."},
        {"prompt": "Elektron memiliki muatan...", "options": ["positif", "negatif", "netral", "ganda"], "answer": "B", "explanation": "Elektron bermuatan negatif."},
        {"prompt": "Isotop adalah atom yang memiliki jumlah proton sama tetapi berbeda jumlah...", "options": ["elektron valensi", "neutron", "kulit", "ion"], "answer": "B", "explanation": "Isotop berbeda pada jumlah neutron."},
        {"prompt": "Nomor massa adalah jumlah...", "options": ["proton + neutron", "proton + elektron", "neutron + elektron", "elektron valensi"], "answer": "A", "explanation": "Nomor massa = proton + neutron."},
    ],
    2: [], 3: [], 4: [], 5: [],
}
DETAILED_BANKS["ikatan-kimia"] = {
    1: [
        {"prompt": "Ikatan ion terbentuk karena...", "options": ["pemakaian elektron bersama", "transfer elektron", "gaya London saja", "pemecahan inti"], "answer": "B", "explanation": "Ikatan ion terjadi melalui transfer elektron."},
        {"prompt": "Ikatan kovalen melibatkan...", "options": ["pemakaian pasangan elektron bersama", "transfer proton", "perubahan neutron", "penguapan"], "answer": "A", "explanation": "Ikatan kovalen memakai elektron bersama."},
        {"prompt": "NaCl merupakan contoh senyawa...", "options": ["ion", "kovalen nonpolar", "logam", "asam amino"], "answer": "A", "explanation": "NaCl terbentuk dari ion Na+ dan Cl-."},
        {"prompt": "H2O memiliki ikatan utama berupa...", "options": ["ion", "kovalen", "logam", "inti"], "answer": "B", "explanation": "Air memiliki ikatan kovalen polar."},
        {"prompt": "Elektronegativitas tinggi berarti atom cenderung...", "options": ["menarik elektron ikatan", "melepas proton", "menjadi neutron", "menghilang"], "answer": "A", "explanation": "Elektronegativitas adalah kemampuan menarik elektron ikatan."},
    ],
    2: [], 3: [], 4: [], 5: [],
}
DETAILED_BANKS["stoikiometri"] = {
    1: [
        {"prompt": "Satuan jumlah zat dalam SI adalah...", "options": ["gram", "mol", "liter", "kelvin"], "answer": "B", "explanation": "Mol adalah satuan jumlah zat."},
        {"prompt": "Bilangan Avogadro bernilai sekitar...", "options": ["6,02 x 10^23", "3,14", "9,8", "1,0 x 10^-7"], "answer": "A", "explanation": "1 mol berisi 6,02 x 10^23 partikel."},
        {"prompt": "Massa molar H2O adalah...", "options": ["10 g/mol", "16 g/mol", "18 g/mol", "20 g/mol"], "answer": "C", "explanation": "H2O = 2(1) + 16 = 18 g/mol."},
        {"prompt": "Koefisien reaksi digunakan untuk menunjukkan perbandingan...", "options": ["massa jenis", "mol", "warna", "suhu"], "answer": "B", "explanation": "Koefisien reaksi menunjukkan perbandingan mol."},
        {"prompt": "Rumus mol dari massa adalah...", "options": ["n = m/Mr", "n = Mr/m", "n = m x Mr", "n = V/T"], "answer": "A", "explanation": "Jumlah mol = massa / massa molar."},
    ],
    2: [], 3: [], 4: [], 5: [],
}


def slugify(value: str) -> str:
    result = value.lower().replace(" ", "-").replace("–", "-").replace("—", "-")
    return "".join(ch for ch in result if ch.isalnum() or ch == "-").strip("-")


def _option_list(values: list[str]) -> list[dict[str, str]]:
    labels = ["A", "B", "C", "D"]
    return [{"id": labels[index], "label": labels[index], "text": value} for index, value in enumerate(values[:4])]


def _pair_list(pairs: dict[str, str]) -> list[dict[str, str]]:
    return [{"left": left, "right": right} for left, right in pairs.items()]


def _generic_question(topic_id: str, topic_title: str, level_id: str, level_number: int, index: int) -> dict[str, Any]:
    quiz_type = QUIZ_LEVEL_TYPES[level_number]
    qid = f"{level_id}-q{index}"
    common = {
        "id": qid,
        "topic_id": topic_id,
        "level_id": level_id,
        "question_type": quiz_type,
        "difficulty": "easy" if level_number <= 2 else "medium" if level_number <= 4 else "hard",
        "order_index": index,
        "is_active": True,
    }
    if quiz_type == "multiple_choice":
        return common | {"prompt": f"Konsep utama nomor {index} pada topik {topic_title} adalah bagian dari...", "options": _option_list(["kimia", "astronomi", "geografi", "sejarah"]), "correct_answer": "A", "matching_pairs": [], "explanation": f"{topic_title} termasuk materi kimia."}
    if quiz_type == "matching":
        pairs = {f"konsep {index}": topic_title, "bidang": "kimia", "tujuan": "pemahaman konsep", "latihan": "soal", "evaluasi": "feedback"}
        return common | {"prompt": f"Cocokkan istilah dasar nomor {index} pada topik {topic_title}.", "options": [], "matching_pairs": _pair_list(pairs), "correct_answer": pairs, "explanation": "Pencocokan membantu menguatkan pemahaman istilah."}
    if quiz_type == "true_false":
        return common | {"prompt": f"Pernyataan nomor {index}: {topic_title} adalah salah satu topik pembelajaran kimia.", "options": [], "correct_answer": True, "matching_pairs": [], "explanation": "Pernyataan benar."}
    if quiz_type == "short_answer":
        return common | {"prompt": f"Jawaban singkat nomor {index}: bidang ilmu utama untuk topik {topic_title} adalah?", "options": [], "correct_answer": {"answer": "kimia", "accepted_answers": ["chemistry"]}, "matching_pairs": [], "explanation": "Jawaban singkat: kimia."}
    return common | {"prompt": f"Studi kasus nomor {index}: siswa menganalisis konsep {topic_title}. Bidang ilmu yang paling tepat adalah...", "options": _option_list(["kimia", "sosiologi", "geologi", "ekonomi"]), "correct_answer": "A", "matching_pairs": [], "explanation": "Kasus tersebut berkaitan dengan konsep kimia."}


def _from_bank(topic_id: str, topic_title: str, level_id: str, level_number: int) -> list[dict[str, Any]]:
    bank = DETAILED_BANKS.get(topic_id, {}).get(level_number) or []
    questions = []
    for index, item in enumerate(bank, start=1):
        quiz_type = QUIZ_LEVEL_TYPES[level_number]
        base = {"id": f"{level_id}-q{index}", "topic_id": topic_id, "level_id": level_id, "question_type": quiz_type, "prompt": item["prompt"], "explanation": item.get("explanation"), "difficulty": "easy" if level_number <= 2 else "medium" if level_number <= 4 else "hard", "order_index": index, "is_active": True}
        if quiz_type in {"multiple_choice", "case_based"}:
            questions.append(base | {"options": _option_list(item["options"]), "correct_answer": item["answer"], "matching_pairs": []})
        elif quiz_type == "matching":
            questions.append(base | {"options": [], "matching_pairs": _pair_list(item["pairs"]), "correct_answer": item["pairs"]})
        elif quiz_type == "true_false":
            questions.append(base | {"options": [], "correct_answer": item["answer"], "matching_pairs": []})
        else:
            questions.append(base | {"options": [], "correct_answer": {"answer": item["answer"], "accepted_answers": item.get("accepted", [])}, "matching_pairs": []})
    while len(questions) < 10:
        questions.append(_generic_question(topic_id, topic_title, level_id, level_number, len(questions) + 1))
    return questions[:10]


def _level(topic_id: str, level_number: int) -> dict[str, Any]:
    quiz_type = QUIZ_LEVEL_TYPES[level_number]
    return {
        "id": f"{topic_id}-level-{level_number}",
        "topic_id": topic_id,
        "level_number": level_number,
        "title": f"Level {level_number}",
        "description": f"Latihan {quiz_type.replace('_', ' ')} untuk topik ini.",
        "quiz_type": quiz_type,
        "unlock_requirement_level": None if level_number == 1 else level_number - 1,
        "xp_reward": 20,
        "passing_score": 70,
        "order_index": level_number,
    }


def seed_topics() -> list[dict[str, Any]]:
    topics = []
    for index, title in enumerate(TOPIC_TITLES, start=1):
        topic_id = slugify(title)
        levels = [_level(topic_id, level_number) for level_number in range(1, 6)]
        questions: list[dict[str, Any]] = []
        for level in levels:
            questions.extend(_from_bank(topic_id, title, level["id"], int(level["level_number"])))
        topics.append({"id": topic_id, "title": title, "description": f"Kuis bertingkat untuk {title}.", "order_index": index, "icon": "flask", "is_active": True, "levels": levels, "questions": questions})
    return topics


QUIZ_SEED_TOPICS = seed_topics()


def find_topic(topic_id: str) -> dict[str, Any] | None:
    return next((topic for topic in QUIZ_SEED_TOPICS if topic["id"] == topic_id), None)


def find_level(topic_id: str, level_id: str | None = None, level_number: int | None = None) -> dict[str, Any] | None:
    topic = find_topic(topic_id)
    if not topic:
        return None
    for level in topic["levels"]:
        if level_id and level["id"] == level_id:
            return level
        if level_number and int(level["level_number"]) == int(level_number):
            return level
    return topic["levels"][0] if not level_id and not level_number else None


def questions_for_level(level_id: str) -> list[dict[str, Any]]:
    for topic in QUIZ_SEED_TOPICS:
        questions = [q for q in topic["questions"] if q["level_id"] == level_id]
        if questions:
            return questions
    return []


def get_fallback_questions(topic_id: str, level_number: int) -> list[dict[str, Any]]:
    level = find_level(topic_id, level_number=level_number)
    if not level:
        return []
    return questions_for_level(level["id"])


def merge_and_dedupe_questions(primary: list[dict[str, Any]], fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for question in [*primary, *fallback]:
        qid = str(question.get("id") or question.get("prompt"))
        if qid in seen:
            continue
        seen.add(qid)
        result.append(question)
    return result
