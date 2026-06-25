# conftest.py — MUST set env vars before any app imports
import os

# Force test mode before Settings() is cached by lru_cache.
# Environment variables override .env values in pydantic-settings.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_MOCK_SERVICES", "true")

from pathlib import Path


def _shorten(text: str, max_len: int = 55) -> str:
    text = str(text or "")
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    rows = []
    seen = set()

    statuses = ["passed", "failed", "skipped", "error", "xfailed", "xpassed"]

    for status in statuses:
        for report in terminalreporter.stats.get(status, []):
            nodeid = getattr(report, "nodeid", "")
            when = getattr(report, "when", "call")

            # Ambil hasil utama test. Jika gagal saat setup, tetap tampilkan.
            if when != "call" and not (getattr(report, "failed", False) or getattr(report, "skipped", False)):
                continue

            if nodeid in seen:
                continue
            seen.add(nodeid)

            file_path, _, test_name = nodeid.partition("::")

            duration = getattr(report, "duration", 0.0)
            outcome = getattr(report, "outcome", status).upper()

            rows.append({
                "status": outcome,
                "file": file_path,
                "test": test_name or "-",
                "duration": f"{duration:.3f}s",
            })

    if not rows:
        return

    rows.sort(key=lambda item: (item["file"], item["test"]))

    terminalreporter.write_sep("=", "LAPORAN UNIT TEST")

    headers = ["No", "Status", "File", "Nama Test", "Durasi"]
    table_rows = []

    for index, row in enumerate(rows, start=1):
        table_rows.append([
            str(index),
            row["status"],
            _shorten(row["file"], 35),
            _shorten(row["test"], 55),
            row["duration"],
        ])

    all_rows = [headers] + table_rows
    widths = [
        max(len(str(row[col])) for row in all_rows)
        for col in range(len(headers))
    ]

    def make_row(values):
        return "| " + " | ".join(
            str(value).ljust(widths[index])
            for index, value in enumerate(values)
        ) + " |"

    separator = "+-" + "-+-".join("-" * width for width in widths) + "-+"

    terminalreporter.write_line(separator)
    terminalreporter.write_line(make_row(headers))
    terminalreporter.write_line(separator)

    for row in table_rows:
        terminalreporter.write_line(make_row(row))

    terminalreporter.write_line(separator)

    total = len(rows)
    passed = sum(1 for row in rows if row["status"] == "PASSED")
    failed = sum(1 for row in rows if row["status"] == "FAILED")
    skipped = sum(1 for row in rows if row["status"] == "SKIPPED")

    terminalreporter.write_line(
        f"Ringkasan: Total={total} | Passed={passed} | Failed={failed} | Skipped={skipped}"
    )
