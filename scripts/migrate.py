from pathlib import Path

FILES = [
    Path("database/supabase/migrations/001_initial_schema.sql"),
    Path("database/supabase/functions/triggers.sql"),
    Path("database/supabase/policies/rls.sql"),
]


def main() -> None:
    print("Migration SQL dibuat untuk Supabase. Jalankan berurutan melalui Supabase CLI atau SQL Editor:")
    for f in FILES:
        print("-", f.resolve())


if __name__ == "__main__":
    main()
