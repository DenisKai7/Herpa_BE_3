def graph_rag_prompt(context: str, query: str, intent: str | None = None) -> str:
    if intent == "image-identification":
        return f"""KONTEKS:
{context}

PERTANYAAN:
{query}

Instruksi khusus identifikasi gambar:
1. Gunakan HASIL IDENTIFIKASI VISUAL sebagai sumber utama identifikasi tanaman.
2. Gunakan DATA KNOWLEDGE GRAPH hanya untuk memverifikasi dan melengkapi informasi (senyawa aktif, kegunaan, famili).
3. JANGAN mengganti kandidat visual dengan nama tanaman dari knowledge graph jika tidak ada kesesuaian visual.
4. Nyatakan confidence dan keterbatasan secara eksplisit.
5. Jika ciri visual tidak cukup, katakan: 'Ciri visual yang terlihat belum cukup untuk identifikasi pasti.'
6. Jangan mengarang ciri visual yang tidak terlihat."""

    return f"""KONTEKS TERVERIFIKASI:
{context}

PERTANYAAN:
{query}

Susun jawaban yang hanya mengklaim fakta yang didukung konteks. Tandai keterbatasan data secara jelas."""
