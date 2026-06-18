def clamp_page(limit: int, offset: int, max_limit: int = 100) -> tuple[int, int]:
    return max(1, min(limit, max_limit)), max(0, offset)
