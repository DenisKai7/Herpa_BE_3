from __future__ import annotations

from typing import Any

QUIZ_LEVEL_TYPES = {
    1: "multiple_choice",
    2: "matching",
    3: "true_false",
    4: "short_answer",
    5: "case_study",
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
    "Kimia Lingkungan",
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
            {
                "prompt": "Seorang siswa membandingkan kereaktifan Na dan Ne yang berada dalam satu periode. Jelaskan perbedaan kereaktifan kimia antara natrium (Na) dan neon (Ne) beserta konsep kuncinya.",
                "case_context": "Natrium (Na) bereaksi hebat saat dimasukkan ke dalam air, sedangkan neon (Ne) tidak menunjukkan reaksi apa pun meskipun berada pada periode yang sama.",
                "keywords": ["elektron valensi", "golongan", "gas mulia", "logam alkali", "stabil"],
                "min_keywords": 2,
                "model_answer": "Natrium adalah logam alkali golongan 1 dengan 1 elektron valensi sehingga sangat tidak stabil dan reaktif. Neon adalah gas mulia golongan 18 dengan konfigurasi elektron stabil (oktet) sehingga tidak reaktif.",
                "explanation": "Perbedaan kereaktifan dipengaruhi konfigurasi elektron kulit terluar (elektron valensi). Na mudah melepas elektron, sedangkan Ne sudah stabil.",
            },
            {
                "prompt": "Mengapa jari-jari atom klorin (Cl) lebih kecil dibandingkan dengan natrium (Na) padahal keduanya berada dalam periode yang sama?",
                "case_context": "Data eksperimen menunjukkan jari-jari atom natrium (Na) adalah 186 pm, sedangkan jari-jari atom klorin (Cl) adalah 99 pm.",
                "keywords": ["muatan inti efektif", "proton", "gaya tarik", "kulit elektron", "inti atom"],
                "min_keywords": 2,
                "model_answer": "Cl memiliki jumlah proton (muatan inti efektif) lebih banyak dibanding Na pada jumlah kulit yang sama, sehingga gaya tarik inti terhadap elektron terluar lebih kuat dan menarik elektron lebih dekat ke inti.",
                "explanation": "Dalam satu periode, bertambahnya proton meningkatkan muatan inti efektif, memperkuat tarikan elektron terluar, sehingga jari-jari mengecil.",
            },
            {
                "prompt": "Jelaskan pembentukan ikatan antara unsur natrium (Na) dan klorin (Cl) dalam pembentukan garam dapur (NaCl) dari sudut pandang transfer elektron.",
                "case_context": "Natrium klorida (NaCl) terbentuk dengan mudah melalui reaksi antara logam natrium yang sangat reaktif dan gas klorin yang beracun.",
                "keywords": ["transfer elektron", "ion", "melepas", "menerima", "ikatan ion"],
                "min_keywords": 2,
                "model_answer": "Atom Na memiliki 1 elektron valensi dan cenderung melepas elektron menjadi kation Na+. Atom Cl memiliki 7 elektron valensi dan cenderung menerima elektron menjadi anion Cl-. Terjadi transfer elektron yang membentuk ikatan ion.",
                "explanation": "Ikatan ionik pada NaCl terbentuk dari gaya elektrostatik antara ion Na+ dan Cl- yang dihasilkan dari proses transfer elektron.",
            },
            {
                "prompt": "Jelaskan karakteristik golongan halogen (Golongan 17) dalam tabel periodik dan mengapa mereka sangat cenderung membentuk senyawa dengan logam alkali.",
                "case_context": "Halogen seperti fluorin dan klorin sangat reaktif dan dapat langsung bereaksi dengan logam alkali membentuk garam halida.",
                "keywords": ["elektron valensi", "menerima", "alkali", "stabil", "oktet"],
                "min_keywords": 2,
                "model_answer": "Halogen memiliki 7 elektron valensi, membutuhkan 1 elektron tambahan untuk mencapai konfigurasi oktet stabil. Logam alkali memiliki 1 elektron valensi yang siap dilepaskan, sehingga keduanya sangat mudah bereaksi.",
                "explanation": "Halogen memiliki keelektronegatifan tinggi dan hanya butuh 1 elektron untuk stabil, berpasangan sempurna dengan logam alkali yang cenderung melepas 1 elektron.",
            },
            {
                "prompt": "Jelaskan mengapa gas mulia (Golongan 18) berada dalam kondisi gas monoatomik dan sulit bereaksi dengan unsur lain pada kondisi standar.",
                "case_context": "Gas mulia seperti helium dan argon ditemukan di alam sebagai atom bebas tunggal (monoatomik) dan tidak mudah membentuk senyawa kimia.",
                "keywords": ["stabil", "elektron valensi", "oktet", "duplet", "penuh"],
                "min_keywords": 2,
                "model_answer": "Gas mulia memiliki kulit elektron terluar yang penuh (oktet/duplet) sehingga energinya sangat stabil. Mereka tidak cenderung melepas, menerima, atau berbagi elektron dengan unsur lain.",
                "explanation": "Konfigurasi elektron yang terisi penuh memberikan kestabilan tinggi sehingga gas mulia bersifat inert dan berada sebagai monoatomik.",
            },
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
    2: [], 3: [], 4: [],
    5: [
        {
            "prompt": "Jelaskan perbedaan mendasar antara isotop karbon-12 dan karbon-14 dari sudut pandang partikel penyusun inti atomnya.",
            "case_context": "Karbon-12 merupakan isotop karbon yang stabil dan melimpah, sedangkan karbon-14 bersifat radioaktif dan digunakan untuk penanggalan arkeologi.",
            "keywords": ["neutron", "proton", "inti atom", "nomor massa", "radioaktif"],
            "min_keywords": 2,
            "model_answer": "Kedua isotop memiliki jumlah proton yang sama yaitu 6. Karbon-12 memiliki 6 neutron (nomor massa 12), sedangkan karbon-14 memiliki 8 neutron (nomor massa 14) di dalam inti atomnya.",
            "explanation": "Isotop adalah atom dari unsur yang sama dengan jumlah proton sama tetapi jumlah neutron berbeda.",
        },
        {
            "prompt": "Jelaskan bagaimana model atom Niels Bohr menyempurnakan kelemahan model atom Rutherford terkait kestabilan orbit elektron.",
            "case_context": "Rutherford mengusulkan elektron mengorbit inti seperti planet, tetapi menurut fisika klasik elektron tersebut seharusnya terus memancarkan energi dan jatuh ke inti.",
            "keywords": ["lintasan stasioner", "tingkat energi", "orbit", "memancarkan", "menyerap"],
            "min_keywords": 2,
            "model_answer": "Bohr mengusulkan bahwa elektron mengorbit inti pada tingkat energi atau lintasan stasioner tertentu tanpa memancarkan radiasi energi. Elektron hanya memancarkan atau menyerap energi jika berpindah lintasan.",
            "explanation": "Model Bohr memperkenalkan konsep kuantisasi tingkat energi orbit elektron untuk menjelaskan kestabilan atom.",
        },
        {
            "prompt": "Jelaskan hubungan antara nomor atom, jumlah proton, dan jumlah elektron pada suatu atom netral serta apa yang terjadi jika atom tersebut kehilangan elektron.",
            "case_context": "Atom magnesium netral memiliki nomor atom 12. Namun, di alam sering dijumpai dalam bentuk ion Mg2+.",
            "keywords": ["proton", "elektron", "ion", "positif", "kehilangan"],
            "min_keywords": 2,
            "model_answer": "Pada atom netral, nomor atom sama dengan jumlah proton and jumlah elektron. Jika atom kehilangan elektron, jumlah proton menjadi lebih banyak dari elektron sehingga membentuk ion positif (kation).",
            "explanation": "Kehilangan elektron menghasilkan ketidakseimbangan muatan sehingga terbentuk kation bermuatan positif.",
        },
        {
            "prompt": "Jelaskan peranan neutron di dalam inti atom dan mengapa inti atom yang memiliki terlalu banyak atau terlalu sedikit neutron cenderung tidak stabil.",
            "case_context": "Gaya repulsi elektromagnetik antar proton yang bermuatan positif di dalam inti sangat besar, tetapi inti atom tidak pecah.",
            "keywords": ["gaya nuklir kuat", "proton", "repulsi", "tidak stabil", "radioaktif"],
            "min_keywords": 2,
            "model_answer": "Neutron berfungsi sebagai perekat yang menghasilkan gaya nuklir kuat untuk mengatasi gaya repulsi elektrostatik antar proton. Ketidakseimbangan rasio neutron/proton membuat inti atom tidak stabil dan bersifat radioaktif.",
            "explanation": "Gaya nuklir kuat antar nukleon (proton dan neutron) menjaga keutuhan inti atom dari gaya tolak-menolak proton.",
        },
        {
            "prompt": "Jelaskan perbedaan muatan dan massa dari tiga partikel subatom penyusun atom (proton, neutron, dan elektron).",
            "case_context": "Struktur atom terdiri dari inti yang padat dikelilingi oleh ruang hampa berisi elektron.",
            "keywords": ["muatan", "massa", "proton", "neutron", "elektron"],
            "min_keywords": 3,
            "model_answer": "Proton bermuatan positif (+1) dan memiliki massa signifikan (~1 sma). Neutron tidak bermuatan (netral) dengan massa ~1 sma. Elektron bermuatan negatif (-1) dengan massa yang sangat kecil (dapat diabaikan).",
            "explanation": "Proton dan neutron membentuk massa inti atom, sedangkan elektron berkontribusi pada volume atom.",
        },
    ]
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
    if quiz_type == "case_study":
        return common | {
            "prompt": f"Studi kasus {index}: Siswa menganalisis konsep {topic_title}. Jelaskan konsep kunci dan mengapa hal tersebut penting.",
            "options": [],
            "matching_pairs": [],
            "correct_answer": {
                "required_keywords": [topic_title.lower(), "kimia"],
                "min_keywords": 1,
                "answer": f"Konsep kunci dalam {topic_title} berkaitan dengan prinsip dasar kimia.",
            },
            "metadata": {"case_context": f"Sebuah analisis tentang topik {topic_title} dilakukan dalam laboratorium kimia medis."},
            "explanation": f"{topic_title} termasuk materi kimia yang penting dipahami.",
        }
    return common | {"prompt": f"Studi kasus nomor {index}: siswa menganalisis konsep {topic_title}. Bidang ilmu yang paling tepat adalah...", "options": _option_list(["kimia", "sosiologi", "geologi", "ekonomi"]), "correct_answer": "A", "matching_pairs": [], "explanation": "Kasus tersebut berkaitan dengan konsep kimia."}


def _from_bank(topic_id: str, topic_title: str, level_id: str, level_number: int) -> list[dict[str, Any]]:
    bank = DETAILED_BANKS.get(topic_id, {}).get(level_number) or []
    questions = []
    for index, item in enumerate(bank, start=1):
        quiz_type = QUIZ_LEVEL_TYPES[level_number]
        base = {"id": f"{level_id}-q{index}", "topic_id": topic_id, "level_id": level_id, "question_type": quiz_type, "prompt": item["prompt"], "explanation": item.get("explanation"), "difficulty": "easy" if level_number <= 2 else "medium" if level_number <= 4 else "hard", "order_index": index, "is_active": True}
        if quiz_type in {"multiple_choice"}:
            questions.append(base | {"options": _option_list(item["options"]), "correct_answer": item["answer"], "matching_pairs": []})
        elif quiz_type == "case_study":
            questions.append(base | {
                "options": [],
                "matching_pairs": [],
                "correct_answer": {
                    "required_keywords": item.get("keywords", []),
                    "min_keywords": item.get("min_keywords", 2),
                    "answer": item.get("model_answer", "") or item.get("answer", ""),
                },
                "metadata": {"case_context": item.get("case_context", "")},
            })
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
