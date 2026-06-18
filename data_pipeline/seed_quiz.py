from pathlib import Path


def main() -> None:
    print(Path("database/supabase/seed.sql").resolve())
    print("Jalankan SQL tersebut melalui Supabase SQL Editor atau migration runner.")


if __name__ == "__main__":
    main()
