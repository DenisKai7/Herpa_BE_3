"""Scheduled cleanup is intentionally explicit; call from a trusted scheduler."""


async def cleanup() -> dict[str, int]:
    return {"temporary_objects_deleted": 0, "orphan_records_deleted": 0}
