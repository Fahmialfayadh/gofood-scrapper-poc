import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


DEFAULT_URL = (
    "https://gofood.co.id/surabaya/restaurant/"
    "mie-mapan-pakuwon-city-mall-0fc57cda-a004-4a16-9b43-2ff88d3c754d"
)
DEFAULT_OUTPUT_JSON = Path("output/json/gofood_profile_mapan.json")
DEFAULT_STORAGE_STATE = Path("output/session/gofood_storage_state.json")


def extract_next_data_payload(html_text: str) -> dict:
    pattern = re.compile(
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(html_text)
    if not match:
        raise ValueError("Tag <script id='__NEXT_DATA__'> tidak ditemukan.")

    raw_json = match.group(1).strip()
    if not raw_json:
        raise ValueError("Payload __NEXT_DATA__ kosong.")

    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gagal parse JSON __NEXT_DATA__: {exc}") from exc


def run(url: str, output_json: Path, storage_state: Path, wait_ms: int, headless: bool) -> int:
    print(f"[EXECUTING] Buka URL profil: {url}")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    storage_state.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )

        context_kwargs: dict = {
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "locale": "id-ID",
            "timezone_id": "Asia/Jakarta",
            "extra_http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            },
            "viewport": {"width": 1366, "height": 768},
        }

        if storage_state.exists():
            context_kwargs["storage_state"] = str(storage_state)
            print(f"[INFO] Memakai storage state: {storage_state}")
        else:
            print(
                f"[WARNING] Storage state tidak ditemukan: {storage_state}. "
                "Lanjut dengan context baru."
            )

        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        response = page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        status = response.status if response else None
        print(f"[RESULT] Status code utama: {status}")
        print(f"[RESULT] URL final: {page.url}")

        try:
            page.wait_for_load_state("networkidle", timeout=25_000)
        except PlaywrightTimeoutError:
            print("[WARNING] networkidle timeout, lanjut ekstraksi dari state saat ini.")

        page.wait_for_timeout(wait_ms)
        html_text = page.content()
        print(f"[INFO] HTML berhasil diambil ({len(html_text)} chars)")

        try:
            payload = extract_next_data_payload(html_text)
        except ValueError as exc:
            print(f"[ERROR] {exc}")
            context.close()
            browser.close()
            return 1

        output_json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        context.storage_state(path=str(storage_state))

        print(f"[DONE] JSON profil tersimpan: {output_json}")
        print(f"[DONE] Storage state diperbarui: {storage_state}")

        context.close()
        browser.close()
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ambil __NEXT_DATA__ dari halaman profil restoran GoFood via Playwright."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="URL profil restoran target.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_JSON),
        help="Path output JSON hasil ekstraksi __NEXT_DATA__.",
    )
    parser.add_argument(
        "--storage-state",
        default=str(DEFAULT_STORAGE_STATE),
        help="Path storage state Playwright (cookie/session).",
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=12000,
        help="Tambahan waktu tunggu setelah load (ms).",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Jalankan browser non-headless (visual).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run(
        url=args.url,
        output_json=Path(args.output),
        storage_state=Path(args.storage_state),
        wait_ms=args.wait_ms,
        headless=not args.headful,
    )


if __name__ == "__main__":
    raise SystemExit(main())
