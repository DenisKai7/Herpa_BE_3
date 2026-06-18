import re
import sys
from pathlib import Path

PATTERNS = [
    re.compile(r"(?i)(service_role_key|neo4j_password|minio_secret_key)\s*=\s*[^<\s][^\s]+"),
    re.compile(r"postgresql://[^:]+:[^<][^@]+@"),
]
SKIP_DIRS = {".git", ".mypy_cache", ".pytest_cache", "__pycache__"}


def main() -> None:
    bad: list[str] = []
    own_path = Path(__file__).resolve()
    for path in Path(".").rglob("*"):
        if (
            not path.is_file()
            or any(part in SKIP_DIRS for part in path.parts)
            or path.resolve() == own_path
            or path.suffix in {".gguf", ".zip", ".pyc"}
        ):
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        if path.name == ".env.example":
            continue
        if any(pattern.search(text) for pattern in PATTERNS):
            bad.append(str(path))
    if bad:
        print("Potential secrets:", *bad, sep="\n")
        sys.exit(1)
    print("No obvious committed secrets found.")


if __name__ == "__main__":
    main()
