from dataclasses import dataclass


@dataclass(slots=True)
class TextChunk:
    index: int
    text: str
    start: int
    end: int


def chunk_text(text: str, chunk_size: int = 1800, overlap: int = 200) -> list[TextChunk]:
    if not text:
        return []
    chunks: list[TextChunk] = []
    start = 0
    index = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        if end < len(text):
            boundary = max(
                text.rfind("\n", start, end),
                text.rfind(". ", start, end),
            )
            if boundary > start + chunk_size // 2:
                end = boundary + 1
        chunks.append(
            TextChunk(
                index=index,
                text=text[start:end].strip(),
                start=start,
                end=end,
            )
        )
        index += 1
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


def select_relevant_chunks(chunks: list[TextChunk], query: str, limit: int = 6) -> list[TextChunk]:
    terms = {term.lower() for term in query.split() if len(term) > 3}
    scored: list[tuple[int, int, TextChunk]] = []
    for chunk in chunks:
        lower = chunk.text.lower()
        score = sum(lower.count(term) for term in terms)
        scored.append((score, -chunk.index, chunk))
    scored.sort(reverse=True, key=lambda item: (item[0], item[1]))
    selected = [item[2] for item in scored[:limit]]
    return sorted(selected, key=lambda chunk: chunk.index)
