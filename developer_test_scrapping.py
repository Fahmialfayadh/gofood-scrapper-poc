"""
GoFood End-to-End Scraping Pipeline (Developer Test)
=====================================================
Satu script yang menjalankan seluruh pipeline:
  1. Session Bootstrap — menembus WAF, simpan cookies/storage state.
  2. Near-Me Outlet Discovery — scroll + intercept API, kumpulkan outlet.
  3. Batch Menu Extraction — buka profil tiap outlet, ekstrak menu.

Output akhir: JSON + CSV katalog menu dari restoran yang ditemukan.

Usage:
  python3 developer_test_scrapping.py --area surabaya --locality sukolilo-restaurants --limit 5
  python3 developer_test_scrapping.py --area surabaya --locality gubeng-restaurants --limit 10 --headful
"""

import argparse
import csv
import json
import random
import re
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

# ── Constants ───────────────────────────────────────────────────────
WIB = timezone(timedelta(hours=7))
OUTPUT_DIR = Path("output")

API_URL_HINTS = (
    "graphql", "api", "search", "outlet", "restaurant", "explore",
    "discover", "nearby", "listing", "catalog", "feed",
)

BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-default-browser-check",
]

CSV_COLUMNS = [
    "restaurant_uid", "restaurant_name", "restaurant_url", "scraped_at",
    "status", "section_uid", "section_name", "section_type",
    "item_uid", "item_name", "item_description", "item_status",
    "price_units", "currency_code", "image_url", "variant_count",
]


def _context_kwargs(storage_state: Path) -> dict:
    """Konfigurasi context browser yang consistent di semua step."""
    kwargs: dict = {
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
        kwargs["storage_state"] = str(storage_state)
    return kwargs


# ═══════════════════════════════════════════════════════════════════
#  STEP 1 — SESSION BOOTSTRAP
# ═══════════════════════════════════════════════════════════════════

def step1_session_bootstrap(
    browser, listing_url: str, storage_state: Path, wait_ms: int,
) -> bool:
    """Buka halaman listing untuk menembus WAF dan menyimpan session."""
    print(f"\n{'='*60}")
    print("[STEP 1] SESSION BOOTSTRAP")
    print(f"{'='*60}")
    print(f"  Target: {listing_url}")

    context = browser.new_context(**_context_kwargs(storage_state))
    page = context.new_page()

    try:
        response = page.goto(listing_url, wait_until="domcontentloaded", timeout=60_000)
        status = response.status if response else None
        print(f"  HTTP status: {status}")
        print(f"  URL final : {page.url}")
    except PlaywrightTimeoutError:
        print("  [ERROR] Timeout saat navigasi ke halaman listing.")
        context.close()
        return False

    try:
        page.wait_for_load_state("networkidle", timeout=20_000)
    except PlaywrightTimeoutError:
        print("  [WARNING] networkidle timeout, lanjut...")

    page.wait_for_timeout(wait_ms)

    html = page.content()
    has_next_data = "__NEXT_DATA__" in html

    # Simpan session
    context.storage_state(path=str(storage_state))
    context.close()

    if has_next_data:
        print("  [OK] __NEXT_DATA__ terdeteksi — session berhasil.")
        return True
    else:
        # Mungkin kena anti-bot, tapi session tetap tersimpan
        html_lower = html.lower()
        if any(m in html_lower for m in ("captcha", "cloudflare", "probe.js", "access denied")):
            print("  [WARNING] Terdeteksi anti-bot challenge.")
            print("  Coba jalankan ulang dengan --headful untuk solve captcha manual.")
            return False
        print("  [WARNING] __NEXT_DATA__ tidak ditemukan, tapi session tersimpan.")
        return True


# ═══════════════════════════════════════════════════════════════════
#  STEP 2 — NEAR-ME OUTLET DISCOVERY
# ═══════════════════════════════════════════════════════════════════

def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _is_outlet(obj: dict) -> bool:
    if not isinstance(obj, dict):
        return False
    has_uid = "uid" in obj
    has_core = isinstance(obj.get("core"), dict) and "displayName" in obj.get("core", {})
    has_name = "displayName" in obj
    return has_uid and (has_core or has_name)


def _is_real_outlet(uid: str, core: dict) -> bool:
    if uid.startswith("CUISINE_"):
        return False
    if not core:
        return False
    location = core.get("location")
    if not isinstance(location, dict):
        return False
    return location.get("latitude") is not None and location.get("longitude") is not None


def _extract_outlets_recursive(node) -> list[dict]:
    results = []
    if isinstance(node, dict):
        if _is_outlet(node):
            results.append(node)
        for v in node.values():
            results.extend(_extract_outlets_recursive(v))
    elif isinstance(node, list):
        for item in node:
            results.extend(_extract_outlets_recursive(item))
    return results


def _normalize_outlet(raw: dict, service_area: str) -> dict | None:
    uid = raw.get("uid")
    if not uid:
        return None

    core = raw.get("core", {}) if isinstance(raw.get("core"), dict) else {}
    delivery = raw.get("delivery", {}) if isinstance(raw.get("delivery"), dict) else {}
    ratings = raw.get("ratings", {}) if isinstance(raw.get("ratings"), dict) else {}

    if not _is_real_outlet(uid, core):
        return None

    display_name = core.get("displayName") or raw.get("displayName") or ""
    if not display_name:
        return None

    path = raw.get("path", "") or ""
    if not path and service_area and display_name:
        slug = _slugify(display_name)
        path = f"/{service_area}/restaurant/{slug}-{uid}"
    full_url = f"https://gofood.co.id{path}" if path else ""

    return {
        "uid": uid,
        "name": display_name,
        "path": path,
        "full_url": full_url,
        "latitude": core.get("location", {}).get("latitude") if isinstance(core.get("location"), dict) else None,
        "longitude": core.get("location", {}).get("longitude") if isinstance(core.get("location"), dict) else None,
        "status": core.get("status"),
        "rating_average": ratings.get("average"),
        "rating_total": ratings.get("total"),
        "delivery_distance_km": delivery.get("distanceKm"),
        "price_level": raw.get("priceLevel"),
    }


def _extract_next_data_outlets(html: str) -> list[dict]:
    match = re.search(
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html, re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []
    try:
        payload = json.loads(match.group(1).strip())
    except json.JSONDecodeError:
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
            for key in ("outlets", "items"):
                nested = item.get(key) if isinstance(item, dict) else None
                if isinstance(nested, list):
                    for sub in nested:
                        if isinstance(sub, dict) and "uid" in sub:
                            outlets.append(sub)
    return outlets


def step2_outlet_discovery(
    browser, nearme_url: str, service_area: str, storage_state: Path,
    max_scrolls: int, patience: int, scroll_delay: float, wait_ms: int,
) -> list[dict]:
    """Scroll halaman near-me, intercept API, kumpulkan outlet unik."""
    print(f"\n{'='*60}")
    print("[STEP 2] OUTLET DISCOVERY (Near-Me Interceptor)")
    print(f"{'='*60}")
    print(f"  Target : {nearme_url}")
    print(f"  Area   : {service_area}")

    outlets_by_uid: dict[str, dict] = {}
    intercepted_count = 0

    def handle_response(response):
        nonlocal intercepted_count
        if response.request.resource_type not in ("fetch", "xhr"):
            return
        url_lower = response.url.lower()
        if not any(hint in url_lower for hint in API_URL_HINTS):
            return
        try:
            body = response.json()
        except Exception:
            return

        found = _extract_outlets_recursive(body)
        new = 0
        for raw in found:
            norm = _normalize_outlet(raw, service_area)
            if norm and norm["uid"] not in outlets_by_uid:
                outlets_by_uid[norm["uid"]] = norm
                new += 1
        if found:
            intercepted_count += 1
            print(f"    [API] {len(found)} outlets ({new} new, {len(outlets_by_uid)} total)")

    context = browser.new_context(**_context_kwargs(storage_state))
    page = context.new_page()
    page.on("response", handle_response)

    try:
        response = page.goto(nearme_url, wait_until="domcontentloaded", timeout=60_000)
        print(f"  HTTP status: {response.status if response else None}")
    except PlaywrightTimeoutError:
        print("  [ERROR] Timeout navigasi near-me.")
        context.close()
        return []

    try:
        page.wait_for_load_state("networkidle", timeout=20_000)
    except PlaywrightTimeoutError:
        pass

    page.wait_for_timeout(wait_ms)

    # Batch awal dari __NEXT_DATA__
    html = page.content()
    initial = _extract_next_data_outlets(html)
    for raw in initial:
        norm = _normalize_outlet(raw, service_area)
        if norm and norm["uid"] not in outlets_by_uid:
            outlets_by_uid[norm["uid"]] = norm
    print(f"  [INITIAL] {len(initial)} raw -> {len(outlets_by_uid)} unik setelah filter")

    # Scroll loop
    print("  [SCROLL] Memulai infinite scroll...")
    scroll_count = 0
    stale_streak = 0

    while scroll_count < max_scrolls and stale_streak < patience:
        scroll_count += 1
        prev = len(outlets_by_uid)

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(scroll_delay)
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except PlaywrightTimeoutError:
            pass

        new_this = len(outlets_by_uid) - prev
        if new_this == 0:
            stale_streak += 1
            print(f"    Scroll {scroll_count}: tanpa data baru (stale {stale_streak}/{patience})")
        else:
            stale_streak = 0
            print(f"    Scroll {scroll_count}: +{new_this} baru (total {len(outlets_by_uid)})")

    context.storage_state(path=str(storage_state))
    context.close()

    outlet_list = sorted(outlets_by_uid.values(), key=lambda o: o["name"])
    print(f"  [DONE] {len(outlet_list)} outlet unik ditemukan. API ditangkap: {intercepted_count}x")
    return outlet_list


# ═══════════════════════════════════════════════════════════════════
#  STEP 3 — BATCH MENU EXTRACTION
# ═══════════════════════════════════════════════════════════════════

_NEXT_DATA_RE = re.compile(
    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def _parse_menu(html: str) -> dict:
    """Ekstrak __NEXT_DATA__ lalu parse menu sections."""
    match = _NEXT_DATA_RE.search(html)
    if not match:
        return {"status": "error", "error": "__NEXT_DATA__ not found", "menu_sections": []}

    try:
        payload = json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return {"status": "error", "error": "JSON decode error", "menu_sections": []}

    page_props = payload.get("props", {}).get("pageProps", {})
    outlet = page_props.get("outlet", {})
    core = outlet.get("core", {}) if isinstance(outlet.get("core"), dict) else {}
    catalog = outlet.get("catalog", {}) if isinstance(outlet.get("catalog"), dict) else {}
    sections_raw = catalog.get("sections", [])

    result = {
        "restaurant_uid": outlet.get("uid") or core.get("uid") or "",
        "restaurant_name": core.get("displayName") or "",
        "restaurant_url": page_props.get("outletUrl") or "",
        "status": "success" if sections_raw else "no_menu",
        "menu_sections": [],
    }

    if not isinstance(sections_raw, list):
        return result

    for section in sections_raw:
        if not isinstance(section, dict):
            continue
        items = []
        for item in (section.get("items") or []):
            if not isinstance(item, dict):
                continue
            price = item.get("price", {}) if isinstance(item.get("price"), dict) else {}
            variants = item.get("variants", []) if isinstance(item.get("variants"), list) else []
            items.append({
                "item_uid": item.get("uid", ""),
                "item_name": item.get("displayName", ""),
                "item_description": item.get("description", ""),
                "item_status": item.get("status"),
                "price_units": price.get("units"),
                "currency_code": price.get("currencyCode", ""),
                "image_url": item.get("imageUrl", ""),
                "variant_count": len(variants),
            })
        result["menu_sections"].append({
            "section_uid": section.get("uid", ""),
            "section_name": section.get("displayName", ""),
            "section_type": section.get("type"),
            "items": items,
        })

    return result


def step3_batch_menu(
    browser, outlets: list[dict], storage_state: Path,
    limit: int, wait_ms: int, delay_min: float, delay_max: float,
) -> list[dict]:
    """Iterasi outlet, buka profil, ekstrak menu."""
    print(f"\n{'='*60}")
    print("[STEP 3] BATCH MENU EXTRACTION")
    print(f"{'='*60}")

    targets = outlets[:limit]
    print(f"  Target: {len(targets)} outlet (dari {len(outlets)} tersedia)")

    if not targets:
        print("  [WARNING] Tidak ada outlet untuk di-scrape.")
        return []

    results: list[dict] = []
    context = browser.new_context(**_context_kwargs(storage_state))
    page = context.new_page()

    for i, outlet in enumerate(targets):
        name = outlet.get("name", "???")
        url = outlet.get("full_url", "")
        uid = outlet.get("uid", "")

        if not url:
            print(f"\n  [{i+1}/{len(targets)}] SKIP {name} — no URL")
            results.append({
                "restaurant_uid": uid, "restaurant_name": name,
                "restaurant_url": "", "scraped_at": datetime.now(WIB).isoformat(),
                "status": "error", "error": "no full_url", "menu_sections": [],
            })
            continue

        print(f"\n  [{i+1}/{len(targets)}] {name}")
        print(f"    URL: {url}")

        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            print(f"    HTTP: {resp.status if resp else '?'}")
        except PlaywrightTimeoutError:
            print(f"    [ERROR] Timeout")
            results.append({
                "restaurant_uid": uid, "restaurant_name": name,
                "restaurant_url": url, "scraped_at": datetime.now(WIB).isoformat(),
                "status": "error", "error": "goto timeout", "menu_sections": [],
            })
            continue
        except Exception as exc:
            print(f"    [ERROR] {exc}")
            results.append({
                "restaurant_uid": uid, "restaurant_name": name,
                "restaurant_url": url, "scraped_at": datetime.now(WIB).isoformat(),
                "status": "error", "error": str(exc), "menu_sections": [],
            })
            continue

        try:
            page.wait_for_load_state("networkidle", timeout=25_000)
        except PlaywrightTimeoutError:
            pass

        page.wait_for_timeout(wait_ms)
        html = page.content()
        record = _parse_menu(html)

        if not record.get("restaurant_uid"):
            record["restaurant_uid"] = uid
        if not record.get("restaurant_name"):
            record["restaurant_name"] = name
        if not record.get("restaurant_url"):
            record["restaurant_url"] = url
        record["scraped_at"] = datetime.now(WIB).isoformat()

        sec_count = len(record.get("menu_sections", []))
        item_count = sum(len(s.get("items", [])) for s in record.get("menu_sections", []))

        if record["status"] == "success":
            print(f"    [OK] {sec_count} sections, {item_count} items")
        elif record["status"] == "no_menu":
            print(f"    [WARN] No menu found")
        else:
            print(f"    [ERROR] {record.get('error', '?')}")

        results.append(record)

        try:
            context.storage_state(path=str(storage_state))
        except Exception:
            pass

        if i < len(targets) - 1:
            delay = random.uniform(delay_min, delay_max)
            print(f"    Waiting {delay:.1f}s...")
            time.sleep(delay)

    context.close()
    return results


# ═══════════════════════════════════════════════════════════════════
#  OUTPUT — JSON + CSV
# ═══════════════════════════════════════════════════════════════════

def flatten_to_csv_rows(results: list[dict]) -> list[dict]:
    rows = []
    for rec in results:
        base = {
            "restaurant_uid": rec.get("restaurant_uid", ""),
            "restaurant_name": rec.get("restaurant_name", ""),
            "restaurant_url": rec.get("restaurant_url", ""),
            "scraped_at": rec.get("scraped_at", ""),
            "status": rec.get("status", ""),
        }
        sections = rec.get("menu_sections", [])
        if not sections:
            rows.append({**base, **{k: "" for k in CSV_COLUMNS if k not in base}})
            continue
        for sec in sections:
            sec_base = {**base,
                "section_uid": sec.get("section_uid", ""),
                "section_name": sec.get("section_name", ""),
                "section_type": sec.get("section_type", ""),
            }
            items = sec.get("items", [])
            if not items:
                rows.append({**sec_base, **{k: "" for k in CSV_COLUMNS if k not in sec_base}})
                continue
            for item in items:
                rows.append({**sec_base,
                    "item_uid": item.get("item_uid", ""),
                    "item_name": item.get("item_name", ""),
                    "item_description": item.get("item_description", ""),
                    "item_status": item.get("item_status", ""),
                    "price_units": item.get("price_units", ""),
                    "currency_code": item.get("currency_code", ""),
                    "image_url": item.get("image_url", ""),
                    "variant_count": item.get("variant_count", ""),
                })
    return rows


def save_outputs(
    outlets: list[dict], menu_results: list[dict],
    outlets_json: Path, menus_json: Path, menus_csv: Path,
):
    """Simpan semua output ke file."""
    for p in (outlets_json, menus_json, menus_csv):
        p.parent.mkdir(parents=True, exist_ok=True)

    # Outlet discovery
    outlets_json.write_text(
        json.dumps(outlets, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(f"  Outlet JSON : {outlets_json} ({len(outlets)} outlets)")

    # Menu JSON
    menus_json.write_text(
        json.dumps(menu_results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(f"  Menu JSON   : {menus_json}")

    # Menu CSV
    rows = flatten_to_csv_rows(menu_results)
    with menus_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Menu CSV    : {menus_csv} ({len(rows)} rows)")


# ═══════════════════════════════════════════════════════════════════
#  MAIN — ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="GoFood End-to-End Scraping Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh:
  python3 developer_test_scrapping.py --area surabaya --locality sukolilo-restaurants --limit 3
  python3 developer_test_scrapping.py --area surabaya --locality gubeng-restaurants --limit 10 --headful
        """,
    )

    # Lokasi
    parser.add_argument("--area", required=True,
                        help="Service area GoFood (contoh: surabaya, jakarta, bandung).")
    parser.add_argument("--locality", required=True,
                        help="Locality/kecamatan (contoh: sukolilo-restaurants, gubeng-restaurants).")

    # Kontrol jumlah
    parser.add_argument("--limit", type=int, default=5,
                        help="Jumlah outlet yang akan di-scrape menunya (default: 5).")

    # Scroll / discovery tuning
    parser.add_argument("--max-scrolls", type=int, default=100,
                        help="Batas scroll saat outlet discovery (default: 100).")
    parser.add_argument("--patience", type=int, default=3,
                        help="Scroll tanpa data baru sebelum stop (default: 3).")
    parser.add_argument("--scroll-delay", type=float, default=2.5,
                        help="Detik jeda per scroll (default: 2.5).")

    # Timing
    parser.add_argument("--wait-ms", type=int, default=8000,
                        help="Extra wait setelah page load, ms (default: 8000).")
    parser.add_argument("--delay-min", type=float, default=3.0,
                        help="Delay minimum antar outlet (detik).")
    parser.add_argument("--delay-max", type=float, default=7.0,
                        help="Delay maksimum antar outlet (detik).")

    # Browser
    parser.add_argument("--headful", action="store_true",
                        help="Jalankan browser non-headless (visual).")

    args = parser.parse_args()

    # ── Derived paths ──
    storage_state = OUTPUT_DIR / "session" / "gofood_storage_state.json"
    outlets_json = OUTPUT_DIR / "json" / f"gofood_{args.locality}_outlets.json"
    menus_json = OUTPUT_DIR / "json" / f"gofood_{args.locality}_menus.json"
    menus_csv = OUTPUT_DIR / "csv" / f"gofood_{args.locality}_menus.csv"

    listing_url = f"https://gofood.co.id/{args.area}/{args.locality}"
    nearme_url = f"{listing_url}/near-me/"

    storage_state.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'#'*60}")
    print(f"  GoFood E2E Pipeline")
    print(f"  Area     : {args.area}")
    print(f"  Locality : {args.locality}")
    print(f"  Limit    : {args.limit} outlet")
    print(f"  Headless : {not args.headful}")
    print(f"{'#'*60}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headful, args=BROWSER_ARGS)

        # ── STEP 1 ──
        ok = step1_session_bootstrap(browser, listing_url, storage_state, args.wait_ms)
        if not ok:
            print("\n[ABORT] Session bootstrap gagal. Coba dengan --headful.")
            browser.close()
            return 1

        # ── STEP 2 ──
        outlets = step2_outlet_discovery(
            browser, nearme_url, args.area, storage_state,
            args.max_scrolls, args.patience, args.scroll_delay, args.wait_ms,
        )
        if not outlets:
            print("\n[ABORT] Tidak ada outlet ditemukan.")
            browser.close()
            return 1

        # ── STEP 3 ──
        menu_results = step3_batch_menu(
            browser, outlets, storage_state,
            args.limit, args.wait_ms, args.delay_min, args.delay_max,
        )

        browser.close()

    # ── SAVE ──
    print(f"\n{'='*60}")
    print("[OUTPUT] Menyimpan hasil...")
    print(f"{'='*60}")
    save_outputs(outlets, menu_results, outlets_json, menus_json, menus_csv)

    # ── SUMMARY ──
    success = sum(1 for r in menu_results if r.get("status") == "success")
    errors = sum(1 for r in menu_results if r.get("status") == "error")
    total_items = sum(
        len(s.get("items", []))
        for r in menu_results for s in r.get("menu_sections", [])
    )

    print(f"\n{'='*60}")
    print(f"[SUMMARY]")
    print(f"  Outlet ditemukan  : {len(outlets)}")
    print(f"  Outlet di-scrape  : {len(menu_results)}")
    print(f"  Success           : {success}")
    print(f"  Error             : {errors}")
    print(f"  Total menu items  : {total_items}")
    print(f"{'='*60}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
