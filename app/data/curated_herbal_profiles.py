"""
Curated herbal profiles — safe, educational fallback data for the detail drawer.

Used when the Knowledge Graph lacks complete data for a given herb.
All content is educational, NOT therapeutic. No specific clinical doses.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------

def _use(title: str, description: str, matched: list[str] | None = None) -> dict[str, Any]:
    return {
        "title": title,
        "description": description,
        "matched_symptoms": matched or [],
        "evidence_level": "traditional",
        "verification_status": "limited",
    }


def _prep(title: str, method_type: str, plant_part: str, ingredients: list[str], steps: list[str], notes: str | None = None) -> dict[str, Any]:
    return {
        "title": title,
        "method_type": method_type,
        "plant_part": plant_part,
        "ingredients": ingredients,
        "steps": steps,
        "notes": notes or "Gunakan sebagai edukasi pengolahan rumah tangga, bukan terapi pengganti obat.",
        "verification_status": "limited",
    }


def _guideline(title: str, description: str, freq: str | None = None, dur: str | None = None) -> dict[str, Any]:
    return {
        "title": title,
        "description": description,
        "frequency_text": freq or "Tidak ada frekuensi klinis baku pada knowledge graph.",
        "duration_text": dur or "Hentikan penggunaan jika muncul keluhan tidak nyaman.",
        "dose_status": "not_clinically_established",
        "verification_status": "limited",
    }


def _warning(title: str, description: str, severity: str = "caution") -> dict[str, Any]:
    return {
        "title": title,
        "description": description,
        "severity": severity,
        "verification_status": "limited",
    }


def _claim(text: str, claim_type: str = "traditional_use") -> dict[str, Any]:
    return {
        "claim_text": text,
        "claim_type": claim_type,
        "evidence_level": "traditional",
    }


def _research(title: str, category: str = "farmakologi herbal") -> dict[str, Any]:
    return {
        "title": title,
        "category": category,
    }


def _source(title: str, description: str) -> dict[str, Any]:
    return {
        "title": title,
        "description": description,
        "evidence_level": "traditional",
    }


# ---------------------------------------------------------------------------
# Profile builder shortcut
# ---------------------------------------------------------------------------

def _profile(
    common_name: str,
    scientific_name: str,
    family: str,
    plant_parts: list[str],
    botanical_summary: str,
    morphology: list[str],
    organoleptic: list[str],
    uses: list[dict],
    preps: list[dict],
    guidelines: list[dict],
    warnings: list[dict] | None = None,
    claims: list[dict] | None = None,
    research_topics: list[dict] | None = None,
) -> dict[str, Any]:
    return {
        "common_name": common_name,
        "scientific_name": scientific_name,
        "family": family,
        "plant_parts": plant_parts,
        "botanical_description": {
            "summary": botanical_summary,
            "morphology": morphology,
            "organoleptic": organoleptic,
        },
        "traditional_uses": uses,
        "preparation_methods": preps,
        "usage_guidelines": guidelines,
        "safety_warnings": warnings or [
            _warning(
                "Peringatan umum",
                "Hati-hati pada ibu hamil, menyusui, anak-anak, pengguna obat rutin, atau penderita penyakit kronis. "
                "Konsultasikan dengan tenaga kesehatan sebelum penggunaan herbal.",
            ),
        ],
        "sources": [
            _source("Knowledge Graph Herbal HERPA", "Data berbasis knowledge graph dan curated herbal profile."),
        ],
        "claims": claims or [],
        "research_topics": research_topics or [],
    }


# ===========================================================================
# CURATED PROFILES — 20 popular Indonesian medicinal herbs
# ===========================================================================

CURATED_HERBAL_PROFILES: dict[str, dict[str, Any]] = {

    # ---- 1. Kunyit ----
    "kunyit": _profile(
        common_name="Kunyit",
        scientific_name="Curcuma longa L.",
        family="Zingiberaceae",
        plant_parts=["Rimpang"],
        botanical_summary=(
            "Kunyit (Curcuma longa L.) adalah tanaman rimpang tahunan dari famili Zingiberaceae. "
            "Rimpangnya berwarna kuning-oranye cerah dan telah digunakan secara luas dalam pengobatan tradisional "
            "Asia Tenggara sebagai antiinflamasi dan pencernaan alami."
        ),
        morphology=[
            "Tinggi tanaman 60-100 cm dengan batang semu tegak.",
            "Rimpang utama berbentuk oval, berwarna kuning-oranye cerah di bagian dalam.",
            "Daun berbentuk lanset memanjang, 30-40 cm, dengan tulang daun tengah menonjol.",
            "Bunga majemuk keluar dari pangkal batang, berwarna putih kekuningan.",
        ],
        organoleptic=[
            "Warna kuning-oranye cerah pada daging rimpang.",
            "Aroma khas aromatik, sedikit pedas.",
            "Rasa agak pahit dan hangat di lidah.",
        ],
        uses=[
            _use("Meringankan peradangan ringan", "Secara tradisional digunakan untuk membantu meringankan keluhan peradangan ringan dan nyeri otot.", ["nyeri", "inflamasi", "peradangan"]),
            _use("Mendukung pencernaan", "Digunakan dalam ramuan tradisional untuk membantu meredakan gangguan pencernaan ringan.", ["mual", "kembung", "pencernaan"]),
        ],
        preps=[
            _prep("Rebusan rimpang", "decoction", "Rimpang", ["Rimpang kunyit segar 2-3 ruas jari", "Air bersih 400 ml"], ["Cuci rimpang kunyit hingga bersih.", "Iris tipis atau memarkan rimpang.", "Rebus dengan air hingga mendidih dan air berkurang sekitar setengah.", "Saring dan biarkan hingga hangat sebelum diminum."]),
            _prep("Jamun tradisional", "infusion", "Rimpang", ["Rimpang kunyit yang sudah diparut 1 sendok makan", "Air hangat 200 ml", "Madu secukupnya (opsional)"], ["Parut rimpang kunyit segar.", "Seduh dengan air hangat.", "Diamkan 10-15 menit, lalu saring.", "Tambahkan madu jika diinginkan."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Gunakan dalam jumlah wajar sebagai ramuan tradisional. Hindari penggunaan berlebihan. Konsultasikan tenaga kesehatan untuk penggunaan rutin."),
        ],
        claims=[
            _claim("Secara tradisional digunakan untuk membantu meringankan keluhan inflamasi ringan."),
            _claim("Memiliki kandungan senyawa kurkuminoid yang diteliti memiliki aktivitas antioksidan."),
        ],
        research_topics=[
            _research("Kajian aktivitas antiinflamasi kurkuminoid"),
            _research("Bioavailabilitas kurkumin dan penyerapan usus"),
        ],
    ),

    # ---- 2. Jahe ----
    "jahe": _profile(
        common_name="Jahe",
        scientific_name="Zingiber officinale Rosc.",
        family="Zingiberaceae",
        plant_parts=["Rimpang"],
        botanical_summary=(
            "Jahe (Zingiber officinale) adalah tanaman rimpang dari famili Zingiberaceae. "
            "Rimpangnya berwarna krem kecokelatan dengan aroma pedas khas. "
            "Digunakan secara luas dalam pengobatan tradisional untuk gangguan pencernaan dan mual."
        ),
        morphology=[
            "Tinggi tanaman 30-100 cm dengan batang semu tegak.",
            "Rimpang berbentuk cabang, berwarna krem kecokelatan di luar, kuning pucat di dalam.",
            "Daun berbentuk lanset, bergantian, dengan panjang 15-25 cm.",
            "Bunga berwarna kuning kehijauan dengan bibir berwarna ungu.",
        ],
        organoleptic=[
            "Warna krem kecokelatan pada kulit rimpang.",
            "Aroma pedas khas yang kuat karena kandungan gingerol.",
            "Rasa pedas dan hangat.",
        ],
        uses=[
            _use("Meringankan mual dan muntah", "Secara tradisional digunakan untuk membantu meredakan mual ringan, mabuk perjalanan, dan muntah.", ["mual", "muntah", "mabuk"]),
            _use("Mendukung pencernaan", "Digunakan untuk membantu meredakan kembung dan gangguan pencernaan ringan.", ["kembung", "pencernaan", "perut kembung"]),
        ],
        preps=[
            _prep("Wedang jahe", "decoction", "Rimpang", ["Rimpang jahe segar 2-3 cm", "Air bersih 300 ml", "Gula merah atau madu secukupnya"], ["Cuci dan memarkan rimpang jahe.", "Rebus dengan air hingga mendidih selama 10-15 menit.", "Saring dan tambahkan pemanis alami jika diinginkan.", "Minum selagi hangat."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Gunakan dalam jumlah wajar. Hindari konsumsi berlebihan karena dapat menyebabkan iritasi lambung pada sebagian orang."),
        ],
        claims=[
            _claim("Secara tradisional digunakan untuk meringankan mual dan gangguan pencernaan ringan."),
        ],
        research_topics=[
            _research("Aktivitas antiemetik senyawa gingerol dan shogaol"),
        ],
    ),

    # ---- 3. Kencur ----
    "kencur": _profile(
        common_name="Kencur",
        scientific_name="Kaempferia galanga L.",
        family="Zingiberaceae",
        plant_parts=["Rimpang"],
        botanical_summary=(
            "Kencur (Kaempferia galanga) adalah tanaman rimpang dari famili Zingiberaceae. "
            "Rimpangnya berwarna putih kekuningan dengan aroma khas yang harum. "
            "Dikenal dalam jamu tradisional Indonesia untuk meredakan batuk dan masuk angin."
        ),
        morphology=[
            "Tinggi tanaman 15-30 cm, termasuk jenis yang pendek.",
            "Rimpang berbentuk bulat telur, berwarna putih kekuningan.",
            "Daun berbentuk bulat telur lebar, 2-4 helai, muncul dari rimpang langsung.",
            "Bunga berwarna putih dengan corak ungu.",
        ],
        organoleptic=[
            "Warna putih kekuningan pada rimpang.",
            "Aroma khas harum, agak pedas.",
            "Rasa pedas dan sedikit pahit.",
        ],
        uses=[
            _use("Meredakan batuk ringan", "Secara tradisional digunakan untuk membantu meredakan batuk dan masuk angin.", ["batuk", "masuk angin", "flu ringan"]),
            _use("Meringankan pegal dan nyeri ringan", "Digunakan dalam bentuk kompres atau minuman untuk membantu meredakan pegal.", ["pegal", "nyeri otot"]),
        ],
        preps=[
            _prep("Beras kencur", "infusion", "Rimpang", ["Rimpang kencur segar 2-3 cm", "Beras putih 2 sendok makan", "Air bersih 300 ml", "Gula merah secukupnya"], ["Rendam beras selama 2-3 jam.", "Cuci bersih dan parut rimpang kencur.", "Rebus beras dan kencur bersama air hingga mendidih.", "Saring, tambahkan gula merah, dan minum hangat."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Gunakan sebagai minuman tradisional sesekali. Tidak dianjurkan untuk penggunaan jangka panjang tanpa pengawasan tenaga kesehatan."),
        ],
    ),

    # ---- 4. Lengkuas ----
    "lengkuas": _profile(
        common_name="Lengkuas",
        scientific_name="Alpinia galanga (L.) Willd.",
        family="Zingiberaceae",
        plant_parts=["Rimpang"],
        botanical_summary=(
            "Lengkuas (Alpinia galanga) adalah tanaman rimpang dari famili Zingiberaceae. "
            "Rimpangnya berwarna putih kecokelatan dan beraroma khas. "
            "Digunakan dalam pengobatan tradisional untuk gangguan pencernaan dan antiinflamasi ringan."
        ),
        morphology=[
            "Tinggi tanaman bisa mencapai 1-2 meter.",
            "Rimpang berwarna putih kecokelatan, lebih keras dari jahe.",
            "Daun berbentuk lanset memanjang, tersusun berseling.",
            "Bunga berwarna putih dengan bibir merah muda.",
        ],
        organoleptic=[
            "Warna putih kecokelatan pada rimpang.",
            "Aroma khas yang segar dan sedikit pedas.",
            "Rasa pedas dan aromatik.",
        ],
        uses=[
            _use("Mendukung pencernaan", "Secara tradisional digunakan untuk membantu mengatasi gangguan pencernaan ringan dan kembung.", ["kembung", "pencernaan", "mual"]),
        ],
        preps=[
            _prep("Irisan lengkuas dalam minuman hangat", "infusion", "Rimpang", ["Lengkuas segar 2-3 cm", "Air panas 250 ml", "Madu secukupnya"], ["Cuci bersih dan iris tipis lengkuas.", "Seduh dengan air panas selama 10 menit.", "Saring dan tambahkan madu jika diinginkan."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Gunakan dalam jumlah wajar sebagai bumbu atau minuman herbal."),
        ],
    ),

    # ---- 5. Temulawak ----
    "temulawak": _profile(
        common_name="Temulawak",
        scientific_name="Curcuma xanthorrhiza Roxb.",
        family="Zingiberaceae",
        plant_parts=["Rimpang"],
        botanical_summary=(
            "Temulawak (Curcuma xanthorrhiza) adalah tanaman rimpang asli Indonesia dari famili Zingiberaceae. "
            "Rimpangnya berwarna kuning-oranye dan telah lama digunakan dalam jamu tradisional "
            "untuk menjaga kesehatan hati dan pencernaan."
        ),
        morphology=[
            "Tinggi tanaman 1-2 meter.",
            "Rimpang utama berbentuk bulat telur, berwarna kuning-oranye di bagian dalam.",
            "Daun berbentuk lanset besar, panjang 40-80 cm.",
            "Bunga muncul sebelum daun, berwarna merah muda keputihan.",
        ],
        organoleptic=[
            "Warna kuning-oranye pada daging rimpang.",
            "Aroma khas yang lebih kuat dari kunyit.",
            "Rasa pahit dan agak pedas.",
        ],
        uses=[
            _use("Menjaga kesehatan fungsi hati", "Secara tradisional digunakan untuk membantu menjaga kesehatan fungsi hati dan merangsang nafsu makan.", ["nafsu makan", "kesehatan hati"]),
            _use("Mendukung pencernaan", "Digunakan untuk membantu meredakan gangguan pencernaan ringan.", ["pencernaan", "kembung"]),
        ],
        preps=[
            _prep("Jamun temulawak", "decoction", "Rimpang", ["Rimpang temulawak segar 2-3 ruas jari", "Air bersih 400 ml", "Gula aren atau madu"], ["Cuci bersih rimpang temulawak.", "Iris tipis atau parut rimpang.", "Rebus dengan air hingga mendidih dan tersisa setengah.", "Saring, tambahkan pemanis, dan minum hangat."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Gunakan dalam jumlah wajar. Penderita gangguan hati atau empedu harus berkonsultasi dengan tenaga kesehatan sebelum menggunakan."),
        ],
        claims=[
            _claim("Secara tradisional digunakan untuk menjaga kesehatan fungsi hati dan pencernaan."),
        ],
    ),

    # ---- 6. Temu ireng ----
    "temu_ireng": _profile(
        common_name="Temu Ireng",
        scientific_name="Curcuma aeruginosa Roxb.",
        family="Zingiberaceae",
        plant_parts=["Rimpang"],
        botanical_summary=(
            "Temu ireng (Curcuma aeruginosa) adalah tanaman rimpang dari famili Zingiberaceae. "
            "Rimpangnya berwarna ungu kehitaman di bagian luar dan biru kehijauan di dalam. "
            "Digunakan dalam jamu tradisional untuk mengatasi keputihan dan menjaga kesehatan reproduksi wanita."
        ),
        morphology=[
            "Tinggi tanaman sekitar 1-1,5 meter.",
            "Rimpang berwarna ungu kehitaman di luar, biru kehijauan di dalam.",
            "Daun berbentuk lanset dengan urat daun berwarna merah keunguan.",
        ],
        organoleptic=[
            "Warna ungu kehitaman pada rimpang.",
            "Aroma khas yang agak getir.",
            "Rasa pahit dan agak sepat.",
        ],
        uses=[
            _use("Menjaga kesehatan reproduksi wanita", "Secara tradisional digunakan untuk membantu mengatasi keputihan dan menjaga kesehatan organ reproduksi wanita.", ["keputihan", "kesehatan reproduksi"]),
        ],
        preps=[
            _prep("Rebusan temu ireng", "decoction", "Rimpang", ["Rimpang temu ireng 2-3 ruas jari", "Air bersih 400 ml"], ["Cuci bersih rimpang.", "Iris tipis rimpang.", "Rebus dengan air hingga mendidih dan tersisa setengah.", "Saring dan minum hangat."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Gunakan dalam jumlah wajar. Ibu hamil sebaiknya menghindari penggunaan tanpa konsultasi dokter."),
        ],
    ),

    # ---- 7. Kunyit putih ----
    "kunyit_putih": _profile(
        common_name="Kunyit Putih",
        scientific_name="Curcuma zedoaria (Berg.) Rosc.",
        family="Zingiberaceae",
        plant_parts=["Rimpang"],
        botanical_summary=(
            "Kunyit putih (Curcuma zedoaria) adalah tanaman rimpang dari famili Zingiberaceae. "
            "Rimpangnya berwarna putih kekuningan dengan aroma khas. "
            "Digunakan dalam pengobatan tradisional untuk antiinflamasi dan menjaga pencernaan."
        ),
        morphology=[
            "Tinggi tanaman sekitar 1-1,5 meter.",
            "Rimpang berwarna putih kekuningan, berdaging tebal.",
            "Daun berbentuk lanset besar dengan bercak ungu di tengah.",
        ],
        organoleptic=[
            "Warna putih kekuningan pada rimpang.",
            "Aroma khas yang harum dan sedikit pedas.",
            "Rasa agak pahit dan aromatik.",
        ],
        uses=[
            _use("Antiinflamasi tradisional", "Secara tradisional digunakan untuk membantu meringankan peradangan ringan.", ["inflamasi", "peradangan"]),
            _use("Menjaga pencernaan", "Digunakan untuk membantu menjaga kesehatan saluran pencernaan.", ["pencernaan"]),
        ],
        preps=[
            _prep("Rebusan kunyit putih", "decoction", "Rimpang", ["Rimpang kunyit putih 2-3 cm", "Air bersih 300 ml"], ["Cuci bersih dan iris tipis rimpang.", "Rebus dengan air hingga mendidih 15 menit.", "Saring dan minum hangat."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Gunakan secukupnya. Hindari penggunaan berlebihan."),
        ],
    ),

    # ---- 8. Daun sirih ----
    "daun_sirih": _profile(
        common_name="Daun Sirih",
        scientific_name="Piper betle L.",
        family="Piperaceae",
        plant_parts=["Daun"],
        botanical_summary=(
            "Daun sirih (Piper betle) adalah tanaman merambat dari famili Piperaceae. "
            "Daunnya berbentuk hati dengan aroma khas yang kuat. "
            "Dikenal luas dalam pengobatan tradisional sebagai antiseptik alami."
        ),
        morphology=[
            "Tanaman merambat dengan batang yang bisa mencapai panjang beberapa meter.",
            "Daun berbentuk hati (jantung), permukaan mengkilap, dengan bau khas yang kuat.",
            "Tulang daun menonjol di bagian bawah.",
        ],
        organoleptic=[
            "Warna hijau tua, mengkilap.",
            "Aroma khas yang kuat dan menyengat.",
            "Rasa pedas dan sedikit pahit.",
        ],
        uses=[
            _use("Antiseptik tradisional", "Secara tradisional digunakan sebagai antiseptik alami untuk menjaga kebersihan mulut dan membantu penyembuhan luka ringan.", ["antiseptik", "luka ringan", "kesehatan mulut"]),
            _use("Menjaga kesehatan organ intim wanita", "Digunakan dalam tradisi penguapan (v-steam) untuk menjaga kebersihan area kewanitaan.", ["keputihan", "kesehatan reproduksi"]),
        ],
        preps=[
            _prep("Rebusan daun sirih untuk kumur", "decoction", "Daun", ["Daun sirih segar 5-7 lembar", "Air bersih 400 ml"], ["Cuci bersih daun sirih.", "Rebus dengan air hingga mendidih selama 10-15 menit.", "Biarkan hangat, lalu gunakan untuk berkumur."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Untuk penggunaan luar. Penggunaan dalam sebaiknya dalam jumlah sangat terbatas dan tidak rutin tanpa pengawasan."),
        ],
        warnings=[
            _warning("Peringatan penggunaan", "Penggunaan daun sirih dalam jumlah berlebihan atau jangka panjang dikaitkan dengan risiko kesehatan tertentu. Gunakan secukupnya.", "caution"),
        ],
    ),

    # ---- 9. Adas ----
    "adas": _profile(
        common_name="Adas",
        scientific_name="Foeniculum vulgare Mill.",
        family="Apiaceae",
        plant_parts=["Biji", "Daun"],
        botanical_summary=(
            "Adas (Foeniculum vulgare) adalah tanaman herba dari famili Apiaceae. "
            "Bijinya beraroma manis khas dan digunakan dalam pengobatan tradisional "
            "untuk membantu meredakan kembung dan menjaga pencernaan."
        ),
        morphology=[
            "Tinggi tanaman 1-2 meter, batang tegak bercabang.",
            "Daun berbentuk filamen halus seperti benang.",
            "Biji berbentuk lonjong, berwarna hijau kecokelatan, beraroma manis.",
        ],
        organoleptic=[
            "Warna hijau kecokelatan pada biji.",
            "Aroma manis khas adas (anis-like).",
            "Rasa manis dan sedikit pedas.",
        ],
        uses=[
            _use("Meredakan kembung dan perut penuh gas", "Secara tradisional digunakan untuk membantu meredakan kembung, kolik, dan gangguan pencernaan ringan.", ["kembung", "perut kembung", "kolik", "pencernaan"]),
            _use("Melancarkan ASI", "Dipercaya secara tradisional dapat membantu melancarkan produksi ASI.", ["ASI", "menyusui"]),
        ],
        preps=[
            _prep("Seduhan biji adas", "infusion", "Biji", ["Biji adas 1 sendok teh", "Air panas 200 ml"], ["Tumbuk kasar biji adas.", "Seduh dengan air panas dan tutup rapat.", "Diamkan 10-15 menit, saring, dan minum hangat."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Gunakan dalam jumlah kecil. Penggunaan untuk ibu menyusui sebaiknya dengan konsultasi tenaga kesehatan."),
        ],
    ),

    # ---- 10. Kayu manis ----
    "kayu_manis": _profile(
        common_name="Kayu Manis",
        scientific_name="Cinnamomum verum J.Presl",
        family="Lauraceae",
        plant_parts=["Kulit batang"],
        botanical_summary=(
            "Kayu manis (Cinnamomum verum) adalah pohon kecil dari famili Lauraceae. "
            "Kulit batangnya dikeringkan dan digunakan sebagai rempah dan obat tradisional "
            "untuk menjaga kadar gula darah dan pencernaan."
        ),
        morphology=[
            "Pohon kecil hingga sedang, tinggi 10-15 meter.",
            "Kulit batang berwarna cokelat muda, berlapis tipis saat dikeringkan.",
            "Daun berbentuk oval, mengkilap, berwarna hijau tua.",
        ],
        organoleptic=[
            "Warna cokelat muda pada kulit batang kering.",
            "Aroma manis dan hangat yang khas.",
            "Rasa manis, hangat, sedikit pedas.",
        ],
        uses=[
            _use("Menjaga kadar gula darah", "Secara tradisional digunakan sebagai pelengkap diet untuk membantu menjaga kadar gula darah normal.", ["gula darah", "diabetes"]),
            _use("Mendukung pencernaan", "Digunakan untuk membantu meredakan gangguan pencernaan ringan dan kembung.", ["pencernaan", "kembung"]),
        ],
        preps=[
            _prep("Seduhan kayu manis", "infusion", "Kulit batang", ["Kayu manis batangan 1-2 cm atau bubuk 1/2 sendok teh", "Air panas 200 ml"], ["Masukkan kayu manis ke dalam cangkir.", "Seduh dengan air panas dan tutup rapat.", "Diamkan 10-15 menit, saring, dan minum hangat."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Gunakan dalam jumlah kecil. Penggunaan jangka panjang dalam dosis tinggi tidak dianjurkan tanpa pengawasan."),
        ],
        warnings=[
            _warning("Perhatian untuk penderita gangguan hati", "Penggunaan kayu manis dalam jumlah besar dalam jangka panjang dapat memengaruhi fungsi hati. Konsultasikan dengan tenaga kesehatan.", "caution"),
        ],
    ),

    # ---- 11. Sambiloto ----
    "sambiloto": _profile(
        common_name="Sambiloto",
        scientific_name="Andrographis paniculata (Burm.f.) Nees",
        family="Acanthaceae",
        plant_parts=["Daun", "Batang"],
        botanical_summary=(
            "Sambiloto (Andrographis paniculata) adalah tanaman herba dari famili Acanthaceae. "
            "Dikenal dengan rasa sangat pahit dan digunakan dalam pengobatan tradisional "
            "untuk membantu meredakan demam ringan dan menjaga daya tahan tubuh."
        ),
        morphology=[
            "Tinggi tanaman 30-90 cm, batang tegak bercabang.",
            "Daun berbentuk lanset, hijau gelap, berpasangan.",
            "Bunga kecil berwarna putih dengan bercak ungu.",
        ],
        organoleptic=[
            "Warna hijau gelap pada daun.",
            "Aroma agak pahit saat direbus.",
            "Rasa sangat pahit.",
        ],
        uses=[
            _use("Menjaga daya tahan tubuh", "Secara tradisional digunakan untuk membantu menjaga daya tahan tubuh dan meredakan demam ringan.", ["demam", "daya tahan tubuh", "imun"]),
            _use("Meredakan batuk dan pilek ringan", "Digunakan untuk membantu meredakan gejala batuk dan pilek ringan.", ["batuk", "pilek", "flu"]),
        ],
        preps=[
            _prep("Rebusan daun sambiloto", "decoction", "Daun", ["Daun sambiloto segar 5-7 lembar", "Air bersih 400 ml"], ["Cuci bersih daun sambiloto.", "Rebus dengan air hingga mendidih dan tersisa setengah.", "Saring dan minum dalam keadaan hangat."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Gunakan dalam jumlah wajar. Rasa sangat pahit. Ibu hamil sebaiknya menghindari tanaman ini."),
        ],
        warnings=[
            _warning("Kontraindikasi kehamilan", "Tidak dianjurkan untuk ibu hamil karena dapat memengaruhi kontraksi rahim.", "caution"),
        ],
    ),

    # ---- 12. Meniran ----
    "meniran": _profile(
        common_name="Meniran",
        scientific_name="Phyllanthus niruri L.",
        family="Phyllanthaceae",
        plant_parts=["Seluruh tanaman"],
        botanical_summary=(
            "Meniran (Phyllanthus niruri) adalah tanaman herba kecil dari famili Phyllanthaceae. "
            "Seluruh bagian tanaman digunakan dalam pengobatan tradisional "
            "untuk menjaga kesehatan ginjal dan daya tahan tubuh."
        ),
        morphology=[
            "Tinggi tanaman 30-60 cm, batang tegak bercabang.",
            "Daun kecil berbentuk oval, tersusun berpasangan di sepanjang batang.",
            "Buah kecil berbentuk bulat, berwarna hijau kekuningan.",
        ],
        organoleptic=[
            "Warna hijau pada seluruh bagian tanaman.",
            "Aroma ringan, tidak terlalu menyengat.",
            "Rasa agak pahit dan sepat.",
        ],
        uses=[
            _use("Menjaga kesehatan ginjal", "Secara tradisional digunakan untuk membantu menjaga kesehatan fungsi ginjal dan saluran kemih.", ["ginjal", "saluran kemih"]),
            _use("Menjaga daya tahan tubuh", "Digunakan untuk membantu menjaga daya tahan tubuh secara umum.", ["daya tahan tubuh", "imun"]),
        ],
        preps=[
            _prep("Rebusan meniran", "decoction", "Seluruh tanaman", ["Meniran segar 1 genggam (±10-15 batang)", "Air bersih 500 ml"], ["Cuci bersih seluruh tanaman.", "Rebus dengan air hingga mendidih selama 15-20 menit.", "Saring dan minum hangat."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Gunakan dalam jumlah wajar. Penderita gangguan ginjal kronis harus berkonsultasi dengan dokter."),
        ],
    ),

    # ---- 13. Pegagan ----
    "pegagan": _profile(
        common_name="Pegagan",
        scientific_name="Centella asiatica (L.) Urb.",
        family="Apiaceae",
        plant_parts=["Daun", "Seluruh tanaman"],
        botanical_summary=(
            "Pegagan (Centella asiatica) adalah tanaman merambat dari famili Apiaceae. "
            "Daunnya berbentuk ginjal dan digunakan dalam pengobatan tradisional "
            "untuk meningkatkan daya ingat dan menjaga kesehatan kulit."
        ),
        morphology=[
            "Tanaman herba merambat di tanah.",
            "Daun berbentuk ginjal (reniform), tepi bergerigi halus.",
            "Batang merambat dengan akar pada buku-buku.",
        ],
        organoleptic=[
            "Warna hijau segar pada daun.",
            "Aroma ringan dan segar.",
            "Rasa agak pahit dan sepat.",
        ],
        uses=[
            _use("Meningkatkan daya ingat", "Secara tradisional digunakan untuk membantu meningkatkan daya ingat dan fungsi kognitif.", ["daya ingat", "kognitif", "otak"]),
            _use("Menjaga kesehatan kulit", "Digunakan untuk membantu mempercepat penyembuhan luka ringan dan menjaga kesehatan kulit.", ["luka ringan", "kesehatan kulit"]),
        ],
        preps=[
            _prep("Lalapan atau jus pegagan", "fresh_consumption", "Daun", ["Daun pegagan segar 1 genggam", "Air matang 200 ml", "Madu secukupnya (opsional)"], ["Cuci bersih daun pegagan.", "Blender dengan air hingga halus.", "Saring jika diinginkan, tambahkan madu.", "Minum segera."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Dapat dikonsumsi sebagai lalapan atau jus. Hindari penggunaan jangka panjang dalam dosis besar tanpa pengawasan."),
        ],
    ),

    # ---- 14. Daun kelor ----
    "daun_kelor": _profile(
        common_name="Daun Kelor",
        scientific_name="Moringa oleifera Lam.",
        family="Moringaceae",
        plant_parts=["Daun"],
        botanical_summary=(
            "Daun kelor (Moringa oleifera) adalah tanaman pohon dari famili Moringaceae. "
            "Daunnya kaya akan nutrisi dan digunakan dalam pengobatan tradisional "
            "untuk menjaga daya tahan tubuh dan sebagai sumber nutrisi alami."
        ),
        morphology=[
            "Pohon kecil hingga sedang, tinggi 5-10 meter.",
            "Daun majemuk menyirip, berwarna hijau muda.",
            "Bunga berwarna krem, buah berbentuk segitiga memanjang.",
        ],
        organoleptic=[
            "Warna hijau muda pada daun.",
            "Aroma ringan, mirip sayuran hijau.",
            "Rasa agak manis dan sedikit pedas.",
        ],
        uses=[
            _use("Sumber nutrisi alami", "Daun kelor kaya akan vitamin, mineral, dan antioksidan. Secara tradisional digunakan untuk menjaga daya tahan tubuh.", ["daya tahan tubuh", "nutrisi", "gizi"]),
            _use("Menjaga kadar gula darah", "Digunakan secara tradisional untuk membantu menjaga kadar gula darah normal.", ["gula darah"]),
        ],
        preps=[
            _prep("Sayur bening daun kelor", "soup", "Daun", ["Daun kelor segar 1 genggam", "Air bersih 400 ml", "Bawang merah, garam secukupnya"], ["Cuci bersih daun kelor.", "Rebus air hingga mendidih.", "Masukkan bumbu dan daun kelor.", "Masak sebentar hingga daun layu, angkat."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Dapat dikonsumsi sebagai sayuran sehari-hari. Aman dalam jumlah wajar sebagai makanan."),
        ],
    ),

    # ---- 15. Jeruk nipis ----
    "jeruk_nipis": _profile(
        common_name="Jeruk Nipis",
        scientific_name="Citrus aurantiifolia (Christm.) Swingle",
        family="Rutaceae",
        plant_parts=["Buah"],
        botanical_summary=(
            "Jeruk nipis (Citrus aurantiifolia) adalah tanaman buah dari famili Rutaceae. "
            "Buahnya berukuran kecil, berwarna hijau hingga kuning, dengan rasa sangat asam. "
            "Digunakan dalam pengobatan tradisional untuk meredakan batuk dan menjaga daya tahan tubuh."
        ),
        morphology=[
            "Pohon kecil, tinggi 2-5 meter, dengan duri di ketiak daun.",
            "Buah berbentuk bulat, diameter 3-5 cm, berwarna hijau hingga kuning.",
            "Daun berbentuk oval, berwarna hijau mengkilap.",
        ],
        organoleptic=[
            "Warna hijau hingga kuning pada buah.",
            "Aroma segar dan asam yang khas.",
            "Rasa sangat asam.",
        ],
        uses=[
            _use("Meredakan batuk dan tenggorokan tidak nyaman", "Secara tradisional digunakan untuk membantu meredakan batuk dan menjaga kesehatan tenggorokan.", ["batuk", "tenggorokan"]),
            _use("Menjaga daya tahan tubuh", "Kandungan vitamin C alami digunakan untuk membantu menjaga daya tahan tubuh.", ["daya tahan tubuh", "imun"]),
        ],
        preps=[
            _prep("Perasan jeruk nipis dengan madu", "fresh_consumption", "Buah", ["Jeruk nipis 1 buah", "Madu 1 sendok makan", "Air hangat 200 ml"], ["Belah jeruk nipis dan peras airnya.", "Campurkan perasan dengan air hangat dan madu.", "Aduk rata dan minum segera."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Hindari penggunaan pada perut kosong bagi yang memiliki masalah lambung. Gunakan dalam jumlah wajar."),
        ],
        warnings=[
            _warning("Perhatian untuk penderita maag", "Rasa asam jeruk nipis dapat memperburuk gejala maag atau GERD. Hindari konsumsi berlebihan.", "caution"),
        ],
    ),

    # ---- 16. Daun mint ----
    "daun_mint": _profile(
        common_name="Daun Mint",
        scientific_name="Mentha × piperita L.",
        family="Lamiaceae",
        plant_parts=["Daun"],
        botanical_summary=(
            "Daun mint (Mentha × piperita) adalah tanaman herba dari famili Lamiaceae. "
            "Dikenal dengan aroma dan rasa dingin yang menyegarkan. "
            "Digunakan dalam pengobatan tradisional untuk meredakan gangguan pencernaan dan sakit kepala ringan."
        ),
        morphology=[
            "Tanaman herba dengan batang persegi, tinggi 30-90 cm.",
            "Daun berbentuk oval dengan tepi bergerigi, berwarna hijau gelap.",
            "Bunga kecil berwarna ungu, tersusun dalam malai.",
        ],
        organoleptic=[
            "Warna hijau pada daun.",
            "Aroma dingin dan menyegarkan yang khas.",
            "Rasa dingin dan sedikit pedas.",
        ],
        uses=[
            _use("Meredakan gangguan pencernaan", "Secara tradisional digunakan untuk membantu meredakan kembung, mual, dan gangguan pencernaan ringan.", ["kembung", "mual", "pencernaan"]),
            _use("Meredakan sakit kepala ringan", "Aroma mint digunakan untuk membantu meredakan sakit kepala ringan dan hidung tersumbat.", ["sakit kepala", "hidung tersumbat"]),
        ],
        preps=[
            _prep("Teh mint", "infusion", "Daun", ["Daun mint segar 5-10 lembar", "Air panas 200 ml"], ["Cuci bersih daun mint.", "Remas ringan daun untuk mengeluarkan minyak atsiri.", "Seduh dengan air panas, tutup rapat selama 5-10 menit.", "Saring dan minum hangat."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Aman dikonsumsi sebagai teh herbal. Hindari penggunaan minyak esensial mint murni tanpa pengenceran."),
        ],
    ),

    # ---- 17. Daun jambu biji ----
    "daun_jambu_biji": _profile(
        common_name="Daun Jambu Biji",
        scientific_name="Psidium guajava L.",
        family="Myrtaceae",
        plant_parts=["Daun"],
        botanical_summary=(
            "Daun jambu biji (Psidium guajava) berasal dari famili Myrtaceae. "
            "Daun muda digunakan dalam pengobatan tradisional untuk membantu meredakan diare ringan."
        ),
        morphology=[
            "Pohon kecil hingga sedang, tinggi 3-10 meter.",
            "Daun berbentuk oval, berwarna hijau, permukaan agak kasar.",
            "Buah berbentuk bulat, daging buah berwarna putih atau merah.",
        ],
        organoleptic=[
            "Warna hijau pada daun muda.",
            "Aroma ringan, agak sepat.",
            "Rasa sepat dan agak pahit.",
        ],
        uses=[
            _use("Meredakan diare ringan", "Secara tradisional digunakan untuk membantu meredakan diare ringan berkat kandungan tanin pada daun.", ["diare", "mencret", "sakit perut"]),
        ],
        preps=[
            _prep("Rebusan daun jambu biji muda", "decoction", "Daun", ["Daun jambu biji muda 5-7 lembar", "Air bersih 400 ml"], ["Cuci bersih daun jambu biji muda.", "Rebus dengan air hingga mendidih selama 15 menit.", "Saring dan minum hangat."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Gunakan untuk diare ringan. Jika diare berlangsung lebih dari 2 hari atau disertai darah, segera periksa ke tenaga kesehatan."),
        ],
    ),

    # ---- 18. Belimbing wuluh ----
    "belimbing_wuluh": _profile(
        common_name="Belimbing Wuluh",
        scientific_name="Averrhoa bilimbi L.",
        family="Oxalidaceae",
        plant_parts=["Buah"],
        botanical_summary=(
            "Belimbing wuluh (Averrhoa bilimbi) adalah pohon kecil dari famili Oxalidaceae. "
            "Buahnya berbentuk lonjong, berwarna hijau, dengan rasa sangat asam. "
            "Digunakan dalam pengobatan tradisional untuk membantu menurunkan tekanan darah dan meredakan batuk."
        ),
        morphology=[
            "Pohon kecil, tinggi 5-12 meter.",
            "Buah berbentuk silindris lonjong, 4-6 cm, berwarna hijau hingga kekuningan.",
            "Daun majemuk menyirip, berwarna hijau.",
        ],
        organoleptic=[
            "Warna hijau pada buah muda.",
            "Aroma asam segar.",
            "Rasa sangat asam.",
        ],
        uses=[
            _use("Meredakan batuk", "Secara tradisional digunakan untuk membantu meredakan batuk dan menjaga kesehatan tenggorokan.", ["batuk", "tenggorokan"]),
        ],
        preps=[
            _prep("Belimbing wuluh dengan gula", "fresh_consumption", "Buah", ["Belimbing wuluh segar 3-5 buah", "Gula aren atau madu secukupnya", "Air hangat 200 ml"], ["Cuci bersih buah belimbing wuluh.", "Iris tipis atau memarkan.", "Seduh dengan air hangat dan tambahkan pemanis.", "Minum segera."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Hindari konsumsi berlebihan karena kandungan asam oksalat tinggi. Penderita batu ginjal sebaiknya menghindari."),
        ],
        warnings=[
            _warning("Perhatian kandungan asam oksalat", "Mengandung asam oksalat tinggi. Penderita gangguan ginjal atau batu ginjal sebaiknya menghindari konsumsi.", "caution"),
        ],
    ),

    # ---- 19. Serai ----
    "serai": _profile(
        common_name="Serai",
        scientific_name="Cymbopogon citratus (DC.) Stapf",
        family="Poaceae",
        plant_parts=["Batang", "Daun"],
        botanical_summary=(
            "Serai (Cymbopogon citratus) adalah tanaman rumput-rumputan dari famili Poaceae. "
            "Batang dan daunnya beraroma lemon khas. "
            "Digunakan dalam pengobatan tradisional untuk meredakan gangguan pencernaan dan demam ringan."
        ),
        morphology=[
            "Tanaman rumput tahunan, tumbuh berumpun, tinggi 1-2 meter.",
            "Batang berbentuk silindris, berwarna hijau keunguan di pangkal.",
            "Daun panjang dan sempit, beraroma lemon saat diremas.",
        ],
        organoleptic=[
            "Warna hijau keunguan pada pangkal batang.",
            "Aroma lemon khas yang segar.",
            "Rasa sedikit pedas dan aromatik.",
        ],
        uses=[
            _use("Meredakan gangguan pencernaan", "Secara tradisional digunakan untuk membantu meredakan kembung dan gangguan pencernaan ringan.", ["kembung", "pencernaan"]),
            _use("Meredakan demam ringan", "Digunakan dalam ramuan tradisional untuk membantu meredakan demam ringan.", ["demam"]),
        ],
        preps=[
            _prep("Wedang serai", "decoction", "Batang", ["Batang serai 2-3 batang", "Air bersih 400 ml", "Gula aren atau madu secukupnya"], ["Cuci bersih dan memarkan batang serai.", "Rebus dengan air hingga mendidih selama 10-15 menit.", "Saring, tambahkan pemanis, dan minum hangat."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Aman sebagai minuman herbal. Hindari penggunaan minyak atsiri serai murni tanpa pengenceran."),
        ],
    ),

    # ---- 20. Lidah buaya ----
    "lidah_buaya": _profile(
        common_name="Lidah Buaya",
        scientific_name="Aloe vera (L.) Burm.f.",
        family="Asphodelaceae",
        plant_parts=["Daun"],
        botanical_summary=(
            "Lidah buaya (Aloe vera) adalah tanaman sukulen dari famili Asphodelaceae. "
            "Gel transparan dari daunnya digunakan secara luas dalam pengobatan tradisional "
            "untuk perawatan luka bakar ringan dan menjaga kesehatan kulit."
        ),
        morphology=[
            "Tanaman sukulen tanpa batang, tumbuh berumpun dari akar.",
            "Daun tebal, berdaging, berwarna hijau keabu-abuan, tepi berduri kecil.",
            "Gel transparan di bagian dalam daun.",
        ],
        organoleptic=[
            "Warna hijau keabu-abuan pada kulit daun.",
            "Gel bening transparan di bagian dalam.",
            "Gel tidak berbau, rasanya netral hingga sedikit pahit.",
        ],
        uses=[
            _use("Perawatan kulit luar", "Gel lidah buaya digunakan secara topikal untuk membantu meredakan luka bakar ringan, iritasi kulit, dan menjaga kelembapan kulit.", ["luka bakar ringan", "iritasi kulit", "kelembapan kulit"]),
            _use("Menjaga pencernaan", "Gel lidah buaya diminum secara tradisional untuk membantu menjaga kesehatan saluran pencernaan.", ["pencernaan"]),
        ],
        preps=[
            _prep("Gel lidah buaya topikal", "topical", "Daun", ["Daun lidah buaya segar 1 lembar"], ["Cuci bersih daun lidah buaya.", "Potong tepi duri, belah daun memanjang.", "Kumpulkan gel bening dari bagian dalam.", "Oleskan langsung pada kulit yang membutuhkan."]),
        ],
        guidelines=[
            _guideline("Panduan penggunaan edukatif", "Untuk penggunaan luar: oleskan gel tipis-tipis. Untuk penggunaan dalam: pastikan gel bersih dari getah kuning (aloin) yang dapat menyebabkan iritasi lambung."),
        ],
        warnings=[
            _warning("Hindari getah kuning (aloin)", "Getah kuning di bawah kulit daun mengandung aloin yang bersifat laksatif kuat dan dapat menyebabkan kram perut. Pastikan hanya menggunakan gel bening.", "caution"),
        ],
    ),
}


def get_curated_profile(herb_id_or_name: str) -> dict[str, Any] | None:
    """Look up a curated profile by herb ID or common name (case-insensitive)."""
    if not herb_id_or_name:
        return None
    normalized = herb_id_or_name.lower().strip()
    # Direct key match
    if normalized in CURATED_HERBAL_PROFILES:
        return CURATED_HERBAL_PROFILES[normalized]
    # Try common_name match
    for key, profile in CURATED_HERBAL_PROFILES.items():
        if profile.get("common_name", "").lower() == normalized:
            return profile
    # Partial match on common_name
    for key, profile in CURATED_HERBAL_PROFILES.items():
        if normalized in profile.get("common_name", "").lower():
            return profile
    return None


def get_all_curated_common_names() -> list[str]:
    """Return all curated herb common names."""
    return [p["common_name"] for p in CURATED_HERBAL_PROFILES.values()]
