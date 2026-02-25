import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


DEFAULT_URL = "https://gofood.co.id/surabaya/sukolilo-restaurants"
OUTPUT_HTML = Path("output/html/gofood_playwright_output.html")
OUTPUT_SCREENSHOT = Path("output/screenshots/gofood_playwright_screenshot.png")
OUTPUT_COOKIES = Path("output/session/gofood_cookies.json")
OUTPUT_STATE = Path("output/session/gofood_storage_state.json")


def classify_scenario(status_code: int | None, html: str) -> str:
    html_lower = html.lower()
    has_next_data = "__NEXT_DATA__" in html
    has_restaurant_name = any(name in html for name in ("Mie Gacoan", "Kopi Kenangan"))
    has_antibot_marker = any(
        marker in html_lower
        for marker in (
            "access denied",
            "verify you are human",
            "captcha",
            "cf-chl",
            "cloudflare",
            "probe.js",
            "x-waf-captcha",
        )
    )

    if has_next_data:
        return "B (Next.js State)"
    if has_restaurant_name:
        return "A (Jackpot - SSR Rendered)"
    if status_code in (202, 403) or has_antibot_marker:
        return "C (The Wall - Anti Bot)"
    return "D (Empty Skeleton / strict CSR)"


def extract_outlet_names_from_next_data(html: str) -> list[str]:
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html
    )
    if not match:
        return []

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    page_props = payload.get("props", {}).get("pageProps", {})
    contents = page_props.get("contents", [])
    names: list[str] = []
    seen: set[str] = set()

    def push(name: str | None) -> None:
        if name and name not in seen:
            seen.add(name)
            names.append(name)

    for section in contents:
        data = section.get("data")
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict):
                continue

            # Shape 1: outlet object langsung berada di data[]
            push(item.get("core", {}).get("displayName") or item.get("displayName"))

            # Shape 2: outlet object berada di data[].outlets[]
            outlets = item.get("outlets")
            if isinstance(outlets, list):
                for outlet in outlets:
                    if isinstance(outlet, dict):
                        push(
                            outlet.get("core", {}).get("displayName")
                            or outlet.get("displayName")
                        )

            # Shape 3: outlet object berada di data[].items[]
            items = item.get("items")
            if isinstance(items, list):
                for outlet in items:
                    if isinstance(outlet, dict):
                        push(
                            outlet.get("core", {}).get("displayName")
                            or outlet.get("displayName")
                        )

    return names


def run(url: str, headless: bool, wait_ms: int) -> None:
    print(f"[EXECUTING] Playwright membuka URL: {url}")
    for path in (OUTPUT_HTML, OUTPUT_SCREENSHOT, OUTPUT_COOKIES, OUTPUT_STATE):
        path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )

        context_kwargs = {
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

        if OUTPUT_STATE.exists():
            print(f"[INFO] Memakai session lama: {OUTPUT_STATE}")
            context_kwargs["storage_state"] = str(OUTPUT_STATE)
        else:
            print("[INFO] Session baru (belum ada storage state).")

        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        status_code = None
        main_response = page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        if main_response:
            status_code = main_response.status
        print(f"[RESULT] Status code utama: {status_code}")
        print(f"[RESULT] URL final: {page.url}")

        try:
            page.wait_for_load_state("networkidle", timeout=20_000)
        except PlaywrightTimeoutError:
            print("[WARNING] networkidle timeout, lanjut inspeksi konten saat ini.")

        page.wait_for_timeout(wait_ms)

        html = page.content()
        OUTPUT_HTML.write_text(html, encoding="utf-8")
        page.screenshot(path=str(OUTPUT_SCREENSHOT), full_page=True)

        cookies = context.cookies()
        OUTPUT_COOKIES.write_text(
            json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        context.storage_state(path=str(OUTPUT_STATE))

        scenario = classify_scenario(status_code=status_code, html=html)
        outlet_names = extract_outlet_names_from_next_data(html)
        print(f"[DONE] HTML disimpan: {OUTPUT_HTML} ({len(html)} chars)")
        print(f"[DONE] Screenshot disimpan: {OUTPUT_SCREENSHOT}")
        print(f"[DONE] Cookies disimpan: {OUTPUT_COOKIES} ({len(cookies)} cookies)")
        print(f"[DONE] Storage state disimpan: {OUTPUT_STATE}")
        print(f"[DIAGNOSIS] Skenario terdeteksi: {scenario}")
        print(f"[DIAGNOSIS] Ada __NEXT_DATA__? {'__NEXT_DATA__' in html}")
        print(f"[DIAGNOSIS] Outlet dari __NEXT_DATA__: {len(outlet_names)}")
        if outlet_names:
            print(f"[DIAGNOSIS] Contoh outlet: {outlet_names[:5]}")

        context.close()
        browser.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Uji GoFood via Playwright (JS + session/cookie)."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Target URL GoFood")
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Jalankan browser mode visual (non-headless).",
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=12000,
        help="Tambahan waktu tunggu setelah load (ms).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(url=args.url, headless=not args.headful, wait_ms=args.wait_ms)
