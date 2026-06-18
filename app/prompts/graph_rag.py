def graph_rag_prompt(context: str, query: str) -> str:
    return f"""KONTEKS TERVERIFIKASI:
{context}

PERTANYAAN:
{query}

Susun jawaban yang hanya mengklaim fakta yang didukung konteks. Tandai keterbatasan data secara jelas."""
