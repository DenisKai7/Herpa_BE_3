import json, urllib.request


def main() -> None:
    with urllib.request.urlopen("http://localhost:8000/api/v1/health/dependencies", timeout=15) as response:
        print(json.dumps(json.load(response), indent=2))


if __name__ == "__main__":
    main()
