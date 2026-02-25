import argparse
import json
import re
from pathlib import Path


DEFAULT_INPUT_HTML = Path("output/html/gofood_playwright_output.html")
DEFAULT_OUTPUT_JSON = Path("output/json/gofood_next_data.json")


def extract_next_data_payload(html_text: str) -> dict:
    # Match JSON payload inside: <script id="__NEXT_DATA__" ...> ... </script>
    pattern = re.compile(
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(html_text)
    if not match:
        raise ValueError("Tag <script id=\"__NEXT_DATA__\"> tidak ditemukan di HTML.")

    raw_json = match.group(1).strip()
    if not raw_json:
        raise ValueError("Payload __NEXT_DATA__ kosong.")

    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gagal parse JSON __NEXT_DATA__: {exc}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ekstrak __NEXT_DATA__ dari HTML Next.js menjadi file JSON rapi."
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_HTML),
        help="Path file HTML input (default: output/html/gofood_playwright_output.html).",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_JSON),
        help="Path file JSON output (default: output/json/gofood_next_data.json).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"[ERROR] File input tidak ditemukan: {input_path}")
        return 1

    html_text = input_path.read_text(encoding="utf-8")

    try:
        payload = extract_next_data_payload(html_text)
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    top_keys = sorted(payload.keys()) if isinstance(payload, dict) else []
    print(f"[DONE] JSON berhasil diekstrak ke: {output_path}")
    print(f"[INFO] Input HTML: {input_path} ({len(html_text)} chars)")
    print(f"[INFO] Top-level keys: {top_keys}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
