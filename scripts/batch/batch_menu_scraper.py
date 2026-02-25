"""
Batch Menu Scraper (Deep-Dive)
==============================
Iterasi daftar outlet dari near-me interceptor, buka halaman profil
masing-masing restoran via Playwright, ekstrak __NEXT_DATA__,
parse menu (catalog.sections), simpan ke JSON master.

Micro-batching: gunakan --limit dan --offset untuk kontrol batch size.
Polite scraping: jeda random antar outlet.
"""

import argparse
import csv
import json
import random
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

# ── Defaults ────────────────────────────────────────────────────────
DEFAULT_INPUT = Path("output/json/gofood_nearme_outlets.json")
DEFAULT_OUTPUT = Path("output/json/gofood_menus_master.json")
STORAGE_STATE = Path("output/session/gofood_storage_state.json")
DEFAULT_OUTPUT_CSV = Path("output/csv/gofood_menus_master.csv")

WIB = timezone(timedelta(hours=7))


# ── __NEXT_DATA__ extraction ───────────────────────────────────────

_NEXT_DATA_RE = re.compile(
    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def extract_next_data(html: str) -> dict | None:
    """Ekstrak dan parse __NEXT_DATA__ dari HTML. None jika gagal."""
    match = _NEXT_DATA_RE.search(html)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None


# ── Menu parser ────────────────────────────────────────────────────

def parse_menu_from_payload(payload: dict) -> dict:
    """Parse outlet info + menu sections dari __NEXT_DATA__ payload.

    Returns dict dengan keys:
      restaurant_uid, restaurant_name, restaurant_url, status, menu_sections
    """
    page_props = payload.get("props", {}).get("pageProps", {})
    outlet = page_props.get("outlet", {})
    core = outlet.get("core", {}) if isinstance(outlet.get("core"), dict) else {}

    restaurant_uid = outlet.get("uid") or core.get("uid") or ""
    restaurant_name = core.get("displayName") or ""
    restaurant_url = page_props.get("outletUrl") or ""

    catalog = outlet.get("catalog", {}) if isinstance(outlet.get("catalog"), dict) else {}
    sections_raw = catalog.get("sections", [])

    if not isinstance(sections_raw, list) or not sections_raw:
        return {
            "restaurant_uid": restaurant_uid,
            "restaurant_name": restaurant_name,
            "restaurant_url": restaurant_url,
            "status": "no_menu",
            "menu_sections": [],
        }

    menu_sections = []
    for section in sections_raw:
        if not isinstance(section, dict):
            continue

        items_raw = section.get("items", [])
        items = []
        if isinstance(items_raw, list):
            for item in items_raw:
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

        menu_sections.append({
            "section_uid": section.get("uid", ""),
            "section_name": section.get("displayName", ""),
            "section_type": section.get("type"),
            "items": items,
        })

    return {
        "restaurant_uid": restaurant_uid,
        "restaurant_name": restaurant_name,
        "restaurant_url": restaurant_url,
        "status": "success",
        "menu_sections": menu_sections,
    }


# ── CSV flattener ──────────────────────────────────────────────────

CSV_COLUMNS = [
    "restaurant_uid",
    "restaurant_name",
    "restaurant_url",
    "scraped_at",
    "status",
    "section_uid",
    "section_name",
    "section_type",
    "item_uid",
    "item_name",
    "item_description",
    "item_status",
    "price_units",
    "currency_code",
    "image_url",
    "variant_count",
]


def flatten_results_to_rows(results: list[dict]) -> list[dict]:
    """Flatten nested JSON results ke baris-baris datar untuk CSV.

    Setiap baris = satu menu item, dengan info restoran + section di-denormalisasi.
    Restoran tanpa menu (status error/no_menu) tetap muncul sebagai 1 baris.
    """
    rows: list[dict] = []
    for record in results:
        base = {
            "restaurant_uid": record.get("restaurant_uid", ""),
            "restaurant_name": record.get("restaurant_name", ""),
            "restaurant_url": record.get("restaurant_url", ""),
            "scraped_at": record.get("scraped_at", ""),
            "status": record.get("status", ""),
        }

        sections = record.get("menu_sections", [])
        if not sections:
            # Tetap simpan 1 baris untuk tracking restoran error / tanpa menu
            rows.append({**base, "section_uid": "", "section_name": "",
                         "section_type": "", "item_uid": "", "item_name": "",
                         "item_description": "", "item_status": "",
                         "price_units": "", "currency_code": "",
                         "image_url": "", "variant_count": ""})
            continue

        for section in sections:
            sec_base = {
                **base,
                "section_uid": section.get("section_uid", ""),
                "section_name": section.get("section_name", ""),
                "section_type": section.get("section_type", ""),
            }
            items = section.get("items", [])
            if not items:
                # Section tanpa item tetap muncul 1 baris
                rows.append({**sec_base, "item_uid": "", "item_name": "",
                             "item_description": "", "item_status": "",
                             "price_units": "", "currency_code": "",
                             "image_url": "", "variant_count": ""})
                continue

            for item in items:
                rows.append({
                    **sec_base,
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


def export_csv(rows: list[dict], csv_path: Path) -> None:
    """Tulis baris-baris flat ke file CSV."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


# ── Single outlet scraper ─────────────────────────────────────────

def scrape_single_outlet(page, url: str, wait_ms: int) -> dict:
    """Navigasi ke URL outlet, ekstrak __NEXT_DATA__, parse menu.

    Returns dict record (bisa status success/error/no_menu).
    """
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        status_code = response.status if response else None
    except PlaywrightTimeoutError:
        return {"status": "error", "error": "goto timeout"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    # Tunggu networkidle (best effort)
    try:
        page.wait_for_load_state("networkidle", timeout=25_000)
    except PlaywrightTimeoutError:
        pass

    # Extra wait untuk render
    page.wait_for_timeout(wait_ms)

    html = page.content()
    payload = extract_next_data(html)
    if payload is None:
        return {
            "status": "error",
            "error": f"__NEXT_DATA__ not found (HTTP {status_code})",
        }

    return parse_menu_from_payload(payload)


# ── Target loader ──────────────────────────────────────────────────

def load_targets(input_path: Path, offset: int, limit: int) -> list[dict]:
    """Baca outlet JSON, slice sesuai offset+limit."""
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Input bukan array JSON: {input_path}")

    sliced = data[offset : offset + limit]
    return sliced


# ── Main orchestration ─────────────────────────────────────────────

def run(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    output_path = Path(args.output)
    storage_state = Path(args.storage_state)

    if not input_path.exists():
        print(f"[ERROR] File input tidak ditemukan: {input_path}")
        return 1

    targets = load_targets(input_path, args.offset, args.limit)
    if not targets:
        print(f"[WARNING] Tidak ada target (offset={args.offset}, limit={args.limit}).")
        return 0

    print(f"[INFO] {len(targets)} outlet target (offset={args.offset}, limit={args.limit})")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    storage_state.parent.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []

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

        for i, outlet in enumerate(targets):
            idx = args.offset + i + 1
            name = outlet.get("name", "???")
            url = outlet.get("full_url", "")
            uid = outlet.get("uid", "")

            if not url:
                print(f"[{idx}] SKIP {name} -- no full_url")
                results.append({
                    "restaurant_uid": uid,
                    "restaurant_name": name,
                    "restaurant_url": "",
                    "scraped_at": datetime.now(WIB).isoformat(),
                    "status": "error",
                    "error": "no full_url in target data",
                    "menu_sections": [],
                })
                continue

            print(f"\n[{idx}/{args.offset + len(targets)}] Scraping: {name}")
            print(f"  URL: {url}")

            record = scrape_single_outlet(page, url, args.wait_ms)

            # Isi metadata dari target data jika scraper gagal dapat dari halaman
            if not record.get("restaurant_uid"):
                record["restaurant_uid"] = uid
            if not record.get("restaurant_name"):
                record["restaurant_name"] = name
            if not record.get("restaurant_url"):
                record["restaurant_url"] = url

            record["scraped_at"] = datetime.now(WIB).isoformat()

            # Hitung statistik
            section_count = len(record.get("menu_sections", []))
            item_count = sum(
                len(s.get("items", []))
                for s in record.get("menu_sections", [])
            )

            status = record.get("status", "unknown")
            if status == "success":
                print(f"  [OK] {section_count} sections, {item_count} items")
            elif status == "no_menu":
                print(f"  [WARN] No menu catalog found")
            else:
                print(f"  [ERROR] {record.get('error', 'unknown error')}")

            results.append(record)

            # Persist session setelah tiap outlet
            try:
                context.storage_state(path=str(storage_state))
            except Exception:
                pass

            # Polite delay (kecuali outlet terakhir)
            if i < len(targets) - 1:
                delay = random.uniform(args.delay_min, args.delay_max)
                print(f"  Waiting {delay:.1f}s before next outlet...")
                time.sleep(delay)

        context.close()
        browser.close()

    # ── Simpan output JSON ──
    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # ── Simpan output CSV ──
    csv_path = DEFAULT_OUTPUT_CSV
    csv_rows = flatten_results_to_rows(results)
    export_csv(csv_rows, csv_path)

    # Summary
    success = sum(1 for r in results if r.get("status") == "success")
    errors = sum(1 for r in results if r.get("status") == "error")
    no_menu = sum(1 for r in results if r.get("status") == "no_menu")
    total_items = sum(
        len(s.get("items", []))
        for r in results
        for s in r.get("menu_sections", [])
    )

    print(f"\n{'='*60}")
    print(f"[DONE] JSON tersimpan: {output_path}")
    print(f"[DONE] CSV  tersimpan: {csv_path} ({len(csv_rows)} rows)")
    print(f"[STATS] Total: {len(results)} | Success: {success} | Error: {errors} | No Menu: {no_menu}")
    print(f"[STATS] Total menu items: {total_items}")
    print(f"{'='*60}")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch scrape menu restoran GoFood dari daftar outlet."
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT),
                        help="Path JSON daftar outlet target.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT),
                        help="Path output JSON menu master.")
    parser.add_argument("--output-csv", default=None,
                        help="Path output CSV (default: sama dengan --output tapi .csv).")
    parser.add_argument("--storage-state", default=str(STORAGE_STATE),
                        help="Path storage state Playwright.")
    parser.add_argument("--limit", type=int, default=5,
                        help="Jumlah outlet per batch.")
    parser.add_argument("--offset", type=int, default=0,
                        help="Skip N outlet pertama (untuk lanjut batch).")
    parser.add_argument("--delay-min", type=float, default=3.0,
                        help="Delay minimum antar outlet (detik).")
    parser.add_argument("--delay-max", type=float, default=7.0,
                        help="Delay maksimum antar outlet (detik).")
    parser.add_argument("--wait-ms", type=int, default=12000,
                        help="Extra wait setelah page load (ms).")
    parser.add_argument("--headful", action="store_true",
                        help="Jalankan browser non-headless (visual).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
