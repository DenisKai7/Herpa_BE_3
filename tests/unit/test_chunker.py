from app.services.documents.chunker import chunk_text, select_relevant_chunks


def test_chunks_and_selects_relevant_text():
    text = (
        ("kimia dasar. " * 100)
        + "\nJahe mengandung gingerol dan digunakan dalam penelitian.\n"
        + ("teks lain. " * 100)
    )
    chunks = chunk_text(text, chunk_size=300, overlap=20)
    assert len(chunks) > 2
    selected = select_relevant_chunks(chunks, "gingerol jahe", limit=2)
    assert any("gingerol" in c.text.lower() for c in selected)
