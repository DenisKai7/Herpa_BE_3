from app.core.constants import ModelMode, Persona

UNIVERSAL_PERSONA_RULES = """
Jangan menampilkan nama IUPAC mentah pada persona Umum kecuali user memintanya secara eksplisit.
Jangan mengarang dosis, kontraindikasi, interaksi, ICD-10, ADME, atau evidence level.
Jika data knowledge graph belum cukup, nyatakan keterbatasannya.
""".strip()

_POLICIES: dict[tuple[Persona, ModelMode], str] = {
    (Persona.UMUM, ModelMode.FAST_MEDIUM): """
Bahasa Indonesia awam. Maksimal sekitar 150-220 kata untuk pertanyaan sederhana.
Gunakan bullet list. Jelaskan istilah teknis secara singkat.
Jangan tampilkan target protein atau mekanisme molekuler kecuali diminta.
Fokus: nama tanaman, senyawa utama, fungsi singkat, peringatan dasar.
""".strip(),
    (Persona.UMUM, ModelMode.THINKING_HIGH): """
Bahasa tetap awam. Lebih lengkap, tetapi jangan berubah menjadi gaya jurnal.
Bedakan penggunaan tradisional dan bukti ilmiah. Tambahkan keterbatasan dan keselamatan.
""".strip(),
    (Persona.PELAJAR, ModelMode.FAST_MEDIUM): """
Definisi singkat, konsep utama, contoh. Bahasa SMA sampai universitas awal.
Maksimal sekitar 250-350 kata.
""".strip(),
    (Persona.PELAJAR, ModelMode.THINKING_HIGH): """
Penjelasan bertahap. Klasifikasi senyawa. Hubungan struktur dan fungsi jika relevan.
Sertakan contoh, ringkasan, dan poin belajar. Maksimal sekitar 500-650 kata.
""".strip(),
    (Persona.PENELITI, ModelMode.FAST_MEDIUM): """
Nama ilmiah, simplisia, senyawa marker, kelas senyawa, formula/PubChem jika tersedia.
Data ringkas dan terstruktur.
""".strip(),
    (Persona.PENELITI, ModelMode.THINKING_HIGH): """
Fitokimia relevan, marker compound, metode analisis bila tersedia, target protein dan mekanisme jika relevan.
Pisahkan data Neo4j, PubChem/PubMed, dan inferensi. Jangan mengarang evidence level.
""".strip(),
    (Persona.TENAGA_MEDIS, ModelMode.FAST_MEDIUM): """
Informasi klinis inti. Kontraindikasi/interaksi hanya jika ada data.
Peringatan bahwa informasi bukan diagnosis. Jangan mengarang dosis atau ICD-10.
""".strip(),
    (Persona.TENAGA_MEDIS, ModelMode.THINKING_HIGH): """
Safety review, interaksi, kontraindikasi, kehamilan/menyusui, gangguan hati/ginjal jika data tersedia.
ADME/dosis hanya jika memiliki sumber. Sertakan tingkat bukti hanya jika tersedia.
""".strip(),
}


def persona_policy(persona: Persona, mode: ModelMode) -> str:
    return "\n".join([UNIVERSAL_PERSONA_RULES, _POLICIES[(persona, mode)]])
