"""
Near-Me Network Interceptor
============================
Intercept JSON API responses saat Playwright melakukan auto-scroll
di halaman /near-me/ GoFood untuk mengumpulkan seluruh outlet.

Strategi:
1. Navigasi ke URL /near-me/ locality.
2. Ekstrak __NEXT_DATA__ untuk batch awal outlet.
3. Pasang interceptor di event page.on("response").
4. Auto-scroll sampai tidak ada data baru (patience-based stop).
5. Deduplikasi outlet by UID, simpan ke JSON.
"""

import argparse
import json
import re
import time
import unicodedata
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

# ── Defaults ────────────────────────────────────────────────────────
DEFAULT_URL = "https://gofood.co.id/surabaya/sukolilo-restaurants/near-me/"
OUTPUT_FILE = Path("output/json/gofood_nearme_outlets.json")
RAW_RESPONSES_FILE = Path("output/json/gofood_nearme_raw_responses.json")
STORAGE_STATE = Path("output/session/gofood_storage_state.json")

# Keywords untuk filter URL API yang kemungkinan berisi data outlet
API_URL_HINTS = (
    "graphql", "api", "search", "outlet", "restaurant", "explore",
    "discover", "nearby", "listing", "catalog", "feed",
)

# Service area diekstrak dari URL saat runtime (misal "surabaya")
_service_area: str = ""

# ── Mutable state (dikumpulkan oleh interceptor) ────────────────────
intercepted_responses: list[dict] = []
outlets_by_uid: dict[str, dict] = {}


# ── Data helpers ────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    """Konversi display name ke URL slug GoFood-style."""
    # Normalize unicode, lowercase
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    # Ganti non-alphanumeric dengan dash
    text = re.sub(r"[^a-z0-9]+", "-", text)
    # Trim leading/trailing dashes
    return text.strip("-")


def _is_outlet(obj: dict) -> bool:
    """Heuristic: objek punya 'uid' dan nama outlet."""
    if not isinstance(obj, dict):
        return False
    has_uid = "uid" in obj
    has_core = isinstance(obj.get("core"), dict) and "displayName" in obj.get("core", {})
    has_name = "displayName" in obj
    return has_uid and (has_core or has_name)


def _is_real_outlet(uid: str, core: dict) -> bool:
    """Filter out kategori CUISINE_* dan brand General tanpa data."""
    # Skip kategori cuisine
    if uid.startswith("CUISINE_"):
        return False
    # Skip entry tanpa core data (brand "General" placeholder)
    if not core:
        return False
    # Harus punya location (lat/lng) sebagai indikator outlet fisik
    location = core.get("location")
    if not isinstance(location, dict):
        return False
    if location.get("latitude") is None or location.get("longitude") is None:
        return False
    return True


def extract_outlets_from_api_response(body) -> list[dict]:
    """Recursive walk JSON response, cari objek outlet-shaped."""
    results = []

    def _walk(node):
        if isinstance(node, dict):
            if _is_outlet(node):
                results.append(node)
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(body)
    return results


def _build_path(uid: str, display_name: str) -> str:
    """Generate path restoran dari uid + nama, format: /{area}/restaurant/{slug}-{uid}."""
    if not _service_area or not display_name:
        return ""
    slug = _slugify(display_name)
    return f"/{_service_area}/restaurant/{slug}-{uid}"


def normalize_outlet(raw: dict) -> dict | None:
    """Flatten raw outlet dict ke format bersih. None jika invalid."""
    uid = raw.get("uid")
    if not uid:
        return None

    core = raw.get("core", {}) if isinstance(raw.get("core"), dict) else {}
    delivery = raw.get("delivery", {}) if isinstance(raw.get("delivery"), dict) else {}
    ratings = raw.get("ratings", {}) if isinstance(raw.get("ratings"), dict) else {}

    # Filter: skip kategori dan brand placeholder
    if not _is_real_outlet(uid, core):
        return None

    display_name = core.get("displayName") or raw.get("displayName") or ""
    if not display_name:
        return None

    # Path: ambil dari data jika ada, generate jika tidak
    path = raw.get("path", "") or _build_path(uid, display_name)
    full_url = f"https://gofood.co.id{path}" if path else ""

    return {
        "uid": uid,
        "name": display_name,
        "path": path,
        "full_url": full_url,
        "short_link": core.get("shortLink", ""),
        "latitude": core.get("location", {}).get("latitude") if isinstance(core.get("location"), dict) else None,
        "longitude": core.get("location", {}).get("longitude") if isinstance(core.get("location"), dict) else None,
        "status": core.get("status"),
        "rating_average": ratings.get("average"),
        "rating_total": ratings.get("total"),
        "delivery_enabled": delivery.get("enabled"),
        "delivery_max_radius_km": delivery.get("maxRadiusKm"),
        "delivery_distance_km": delivery.get("distanceKm"),
        "delivery_eta_minutes": delivery.get("eta", {}).get("minutes") if isinstance(delivery.get("eta"), dict) else None,
        "price_level": raw.get("priceLevel"),
        "image_url": (
            raw.get("media", {}).get("logo", "")
            if isinstance(raw.get("media"), dict) else
            core.get("media", {}).get("logo", "") if isinstance(core.get("media"), dict) else ""
        ),
    }


# ── __NEXT_DATA__ extraction ───────────────────────────────────────

def extract_next_data_outlets(html: str) -> list[dict]:
    """Ekstrak outlet dari __NEXT_DATA__ script tag (batch awal)."""
    match = re.search(
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html, re.IGNORECASE | re.DOTALL,
    )
    if not match:
        print("[WARNING] __NEXT_DATA__ tidak ditemukan di HTML.")
        return []

    try:
        payload = json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        print("[WARNING] __NEXT_DATA__ gagal di-parse sebagai JSON.")
        return []

    contents = payload.get("props", {}).get("pageProps", {}).get("contents", [])
    outlets = []
    for section in contents:
        if not isinstance(section, dict):
            continue
        data = section.get("data")
        if not isinstance(data, list):
            continue
        for item in data:
            if isinstance(item, dict) and "uid" in item:
                outlets.append(item)
            # Cek nested outlets[] dan items[] (Shape 2/3 dari existing script)
            for nested_key in ("outlets", "items"):
                nested = item.get(nested_key) if isinstance(item, dict) else None
                if isinstance(nested, list):
                    for sub in nested:
                        if isinstance(sub, dict) and "uid" in sub:
                            outlets.append(sub)
    return outlets


# ── Network interceptor ────────────────────────────────────────────

def handle_response(response):
    """Playwright response callback: tangkap JSON API responses."""
    if response.request.resource_type not in ("fetch", "xhr"):
        return

    url_lower = response.url.lower()
    if not any(hint in url_lower for hint in API_URL_HINTS):
        return

    try:
        body = response.json()
    except Exception:
        return

    packet = {
        "url": response.url,
        "method": response.request.method,
        "status": response.status,
        "post_data": response.request.post_data,
        "response": body,
    }
    intercepted_responses.append(packet)

    found = extract_outlets_from_api_response(body)
    new_count = 0
    for outlet_raw in found:
        normalized = normalize_outlet(outlet_raw)
        if normalized and normalized["uid"] not in outlets_by_uid:
            outlets_by_uid[normalized["uid"]] = normalized
            new_count += 1

    if found:
        print(
            f"  [INTERCEPTED] {response.url[:80]}... -> "
            f"{len(found)} outlets ({new_count} new, {len(outlets_by_uid)} total)"
        )


# ── Scroll engine ──────────────────────────────────────────────────

def scroll_until_exhausted(page, max_scrolls: int, patience: int, scroll_delay: float) -> int:
    """Auto-scroll dengan dynamic stop. Return jumlah total scroll."""
    scroll_count = 0
    stale_streak = 0

    while scroll_count < max_scrolls and stale_streak < patience:
        scroll_count += 1
        prev_total = len(outlets_by_uid)

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        time.sleep(scroll_delay)
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except PlaywrightTimeoutError:
            pass

        current_total = len(outlets_by_uid)
        new_this_scroll = current_total - prev_total

        if new_this_scroll == 0:
            stale_streak += 1
            print(
                f"  [SCROLL {scroll_count}] Tidak ada outlet baru "
                f"(stale streak: {stale_streak}/{patience})"
            )
        else:
            stale_streak = 0
            print(
                f"  [SCROLL {scroll_count}] +{new_this_scroll} outlet baru "
                f"(total: {current_total})"
            )

    if stale_streak >= patience:
        print(f"[DONE] Berhenti: {patience} scroll berturut tanpa data baru.")
    else:
        print(f"[DONE] Berhenti: mencapai batas max_scrolls ({max_scrolls}).")

    return scroll_count


# ── Main orchestration ──────────────────────────────────────────────

def run(args: argparse.Namespace) -> int:
    global _service_area

    output_path = Path(args.output)
    storage_state = Path(args.storage_state)

    # Ekstrak service_area dari URL (misal "surabaya" dari ".../surabaya/sukolilo-restaurants/near-me/")
    url_match = re.search(r"gofood\.co\.id/([^/]+)/", args.url)
    _service_area = url_match.group(1) if url_match else ""
    if _service_area:
        print(f"[INFO] Service area terdeteksi: {_service_area}")

    for p in (output_path, storage_state):
        p.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=not args.headful,
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
            print(f"[WARNING] Storage state tidak ditemukan: {storage_state}. Session baru.")

        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        # Pasang interceptor SEBELUM navigasi
        page.on("response", handle_response)

        # Navigasi ke halaman near-me
        print(f"[PROCESS] Navigasi ke: {args.url}")
        response = page.goto(args.url, wait_until="domcontentloaded", timeout=60_000)
        status = response.status if response else None
        print(f"[RESULT] Status: {status}, URL: {page.url}")

        try:
            page.wait_for_load_state("networkidle", timeout=20_000)
        except PlaywrightTimeoutError:
            print("[WARNING] networkidle timeout pada initial load.")

        page.wait_for_timeout(args.wait_ms)

        # Ekstrak __NEXT_DATA__ untuk batch awal
        html = page.content()
        initial_outlets = extract_next_data_outlets(html)
        for raw in initial_outlets:
            normalized = normalize_outlet(raw)
            if normalized and normalized["uid"] not in outlets_by_uid:
                outlets_by_uid[normalized["uid"]] = normalized
        print(
            f"[INITIAL] {len(initial_outlets)} outlets dari __NEXT_DATA__, "
            f"{len(outlets_by_uid)} unik setelah normalisasi."
        )

        # Scroll loop
        print("[PROCESS] Memulai scroll interception loop...")
        total_scrolls = scroll_until_exhausted(
            page,
            max_scrolls=args.max_scrolls,
            patience=args.patience,
            scroll_delay=args.scroll_delay,
        )

        # Simpan session
        context.storage_state(path=str(storage_state))
        context.close()
        browser.close()

    # Simpan output
    outlet_list = sorted(outlets_by_uid.values(), key=lambda o: o["name"])
    output_path.write_text(
        json.dumps(outlet_list, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\n[SUCCESS] {len(outlet_list)} outlet unik tersimpan ke: {output_path}")
    print(f"[STATS] Total scrolls: {total_scrolls}, API responses ditangkap: {len(intercepted_responses)}")

    # Opsional: simpan raw responses untuk debugging
    if args.save_raw:
        RAW_RESPONSES_FILE.parent.mkdir(parents=True, exist_ok=True)
        RAW_RESPONSES_FILE.write_text(
            json.dumps(intercepted_responses, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[DEBUG] Raw API responses tersimpan ke: {RAW_RESPONSES_FILE}")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Intercept GoFood near-me API responses via Playwright scroll."
    )
    parser.add_argument("--url", default=DEFAULT_URL,
                        help="URL near-me locality target.")
    parser.add_argument("--output", default=str(OUTPUT_FILE),
                        help="Path output JSON hasil intercept.")
    parser.add_argument("--storage-state", default=str(STORAGE_STATE),
                        help="Path storage state Playwright.")
    parser.add_argument("--headful", action="store_true",
                        help="Jalankan browser non-headless (visual).")
    parser.add_argument("--max-scrolls", type=int, default=100,
                        help="Batas maksimum jumlah scroll.")
    parser.add_argument("--patience", type=int, default=3,
                        help="Scroll berturut tanpa data baru sebelum berhenti.")
    parser.add_argument("--scroll-delay", type=float, default=2.5,
                        help="Detik menunggu setelah tiap scroll.")
    parser.add_argument("--save-raw", action="store_true",
                        help="Simpan raw API responses ke file terpisah.")
    parser.add_argument("--wait-ms", type=int, default=5000,
                        help="Tambahan waktu tunggu setelah initial page load (ms).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
