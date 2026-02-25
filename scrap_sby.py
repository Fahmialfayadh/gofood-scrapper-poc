"""
GoFood Surabaya Multi-Area Scraper
====================================
Scrape semua kecamatan di Surabaya secara berurutan dengan delay manusiawi
agar tidak terdeteksi sebagai bot.

Usage:
  python3 scrap_sby.py
  python3 scrap_sby.py --headful          # kalau perlu solve captcha manual
  python3 scrap_sby.py --limit 10         # scrape 10 outlet per area
  python3 scrap_sby.py --start-from 3     # mulai dari area ke-3 (skip yg sudah)
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from developer_test_scrapping import (
    BROWSER_ARGS,
    OUTPUT_DIR,
    _context_kwargs,
    flatten_to_csv_rows,
    save_outputs,
    step1_session_bootstrap,
    step2_outlet_discovery,
    step3_batch_menu,
)

# ── Konfigurasi ────────────────────────────────────────────────────
WIB = timezone(timedelta(hours=7))
CITY = "surabaya"

# Daftar lengkap kecamatan di Surabaya
LIST_AREA = [
    "sukolilo-restaurants",
    "gubeng-restaurants",
    "wonokromo-restaurants",
    "tandes-restaurants",
    "tambaksari-restaurants",
    "mulyorejo-restaurants",

]

# Hapus duplikat sambil pertahankan urutan
_seen = set()
LIST_AREA = [a for a in LIST_AREA if not (a in _seen or _seen.add(a))]


def human_delay(min_sec: float, max_sec: float, label: str = ""):
    """Delay acak yang meniru perilaku manusia."""
    delay = random.uniform(min_sec, max_sec)
    if label:
        print(f"\n  ⏳ {label} — menunggu {delay:.0f} detik...")
    else:
        print(f"\n  ⏳ Menunggu {delay:.0f} detik sebelum area berikutnya...")
    time.sleep(delay)


def run_pipeline_for_area(
    browser,
    area: str,
    storage_state: Path,
    limit: int,
    wait_ms: int,
    headful: bool,
) -> dict:
    """Jalankan pipeline lengkap (step 1-3) untuk satu area."""

    listing_url = f"https://gofood.co.id/{CITY}/{area}"
    nearme_url = f"{listing_url}/near-me/"

    area_label = area.replace("-restaurants", "").replace("-", " ").title()
    started = datetime.now(WIB)

    print(f"\n{'#'*60}")
    print(f"  🏙  AREA: {area_label}")
    print(f"  URL : {listing_url}")
    print(f"  Waktu mulai: {started.strftime('%H:%M:%S WIB')}")
    print(f"{'#'*60}")

    result = {
        "area": area,
        "area_label": area_label,
        "started_at": started.isoformat(),
        "outlets_found": 0,
        "outlets_scraped": 0,
        "success": 0,
        "errors": 0,
        "total_items": 0,
        "status": "pending",
    }

    # ── STEP 1: Session Bootstrap ──
    ok = step1_session_bootstrap(browser, listing_url, storage_state, wait_ms)
    if not ok:
        print(f"  [SKIP] Session bootstrap gagal untuk {area_label}.")
        result["status"] = "session_failed"
        return result

    # Delay setelah bootstrap (manusiawi: orang baca dulu halamannya)
    human_delay(5, 12, "Membaca halaman listing")

    # ── STEP 2: Outlet Discovery ──
    outlets = step2_outlet_discovery(
        browser=browser,
        nearme_url=nearme_url,
        service_area=CITY,
        storage_state=storage_state,
        max_scrolls=150,
        patience=4,
        scroll_delay=random.uniform(2.0, 4.0),  # variasi scroll speed
        wait_ms=wait_ms,
    )

    result["outlets_found"] = len(outlets)

    if not outlets:
        print(f"  [SKIP] Tidak ada outlet ditemukan di {area_label}.")
        result["status"] = "no_outlets"
        return result

    # Delay setelah discovery (manusiawi: scroll panjang lalu istirahat)
    human_delay(8, 18, "Istirahat setelah scrolling")

    # ── STEP 3: Batch Menu Extraction ──
    menu_results = step3_batch_menu(
        browser=browser,
        outlets=outlets,
        storage_state=storage_state,
        limit=limit,
        wait_ms=wait_ms,
        delay_min=4.0,   # delay antar outlet lebih panjang
        delay_max=10.0,
    )

    result["outlets_scraped"] = len(menu_results)
    result["success"] = sum(1 for r in menu_results if r.get("status") == "success")
    result["errors"] = sum(1 for r in menu_results if r.get("status") == "error")
    result["total_items"] = sum(
        len(s.get("items", []))
        for r in menu_results
        for s in r.get("menu_sections", [])
    )
    result["status"] = "done"
    result["finished_at"] = datetime.now(WIB).isoformat()

    # ── Simpan output per area ──
    outlets_json = OUTPUT_DIR / "json" / f"gofood_{area}_outlets.json"
    menus_json = OUTPUT_DIR / "json" / f"gofood_{area}_menus.json"
    menus_csv = OUTPUT_DIR / "csv" / f"gofood_{area}_menus.csv"

    print(f"\n  💾 Menyimpan data {area_label}...")
    save_outputs(outlets, menu_results, outlets_json, menus_json, menus_csv)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="GoFood Surabaya Multi-Area Scraper",
    )
    parser.add_argument(
        "--limit", type=int, default=20,
        help="Jumlah outlet per area yang di-scrape menunya (default: 20).",
    )
    parser.add_argument(
        "--wait-ms", type=int, default=8000,
        help="Extra wait setelah page load dalam ms (default: 8000).",
    )
    parser.add_argument(
        "--headful", action="store_true",
        help="Jalankan browser non-headless (visual).",
    )
    parser.add_argument(
        "--start-from", type=int, default=1,
        help="Mulai dari area ke-N (1-based). Berguna untuk resume. (default: 1)",
    )
    args = parser.parse_args()

    storage_state = OUTPUT_DIR / "session" / "gofood_storage_state.json"
    storage_state.parent.mkdir(parents=True, exist_ok=True)

    # Progress log — untuk resume jika gagal di tengah
    progress_file = OUTPUT_DIR / "json" / "scrap_sby_progress.json"
    progress_file.parent.mkdir(parents=True, exist_ok=True)

    areas_to_scrape = LIST_AREA[args.start_from - 1:]
    total_areas = len(areas_to_scrape)

    print(f"\n{'='*60}")
    print(f"  🚀 GoFood Surabaya Multi-Area Scraper")
    print(f"  Total area   : {total_areas} kecamatan")
    print(f"  Limit/area   : {args.limit} outlet")
    print(f"  Headless     : {not args.headful}")
    print(f"  Start from   : area ke-{args.start_from}")
    print(f"  Waktu mulai  : {datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S WIB')}")
    print(f"{'='*60}")

    all_results = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headful, args=BROWSER_ARGS)

        for idx, area in enumerate(areas_to_scrape, start=1):
            area_label = area.replace("-restaurants", "").replace("-", " ").title()

            print(f"\n\n{'*'*60}")
            print(f"  📍 AREA {idx}/{total_areas}: {area_label}")
            print(f"{'*'*60}")

            try:
                result = run_pipeline_for_area(
                    browser=browser,
                    area=area,
                    storage_state=storage_state,
                    limit=args.limit,
                    wait_ms=args.wait_ms,
                    headful=args.headful,
                )
            except Exception as exc:
                print(f"\n  ❌ ERROR pada {area_label}: {exc}")
                result = {
                    "area": area,
                    "area_label": area_label,
                    "status": "exception",
                    "error": str(exc),
                }

            all_results.append(result)

            # Simpan progress setiap selesai 1 area
            progress_file.write_text(
                json.dumps(all_results, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"\n  📊 Progress tersimpan: {progress_file}")

            # Delay panjang antar area (manusiawi: pindah kecamatan)
            if idx < total_areas:
                human_delay(
                    30, 90,
                    f"Jeda panjang sebelum area berikutnya ({idx}/{total_areas} selesai)",
                )

        browser.close()

    # ── RINGKASAN AKHIR ──
    print(f"\n\n{'='*60}")
    print(f"  📋 RINGKASAN AKHIR — Surabaya Scraping")
    print(f"{'='*60}")

    total_outlets = 0
    total_scraped = 0
    total_success = 0
    total_errors = 0
    total_items = 0

    for r in all_results:
        status_icon = {
            "done": "✅",
            "no_outlets": "⚠️",
            "session_failed": "❌",
            "exception": "💥",
        }.get(r.get("status", "?"), "❓")

        print(f"  {status_icon} {r.get('area_label', r.get('area', '?')):30s}"
              f"  outlets={r.get('outlets_found', 0):3d}"
              f"  scraped={r.get('outlets_scraped', 0):3d}"
              f"  items={r.get('total_items', 0):4d}"
              f"  [{r.get('status', '?')}]")

        total_outlets += r.get("outlets_found", 0)
        total_scraped += r.get("outlets_scraped", 0)
        total_success += r.get("success", 0)
        total_errors += r.get("errors", 0)
        total_items += r.get("total_items", 0)

    print(f"\n  {'─'*50}")
    print(f"  Total outlet ditemukan  : {total_outlets}")
    print(f"  Total outlet di-scrape  : {total_scraped}")
    print(f"  Total success           : {total_success}")
    print(f"  Total error             : {total_errors}")
    print(f"  Total menu items        : {total_items}")
    print(f"  Waktu selesai           : {datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S WIB')}")
    print(f"{'='*60}\n")

    # Simpan ringkasan akhir
    summary_file = OUTPUT_DIR / "json" / "scrap_sby_summary.json"
    summary = {
        "city": CITY,
        "total_areas": total_areas,
        "total_outlets_found": total_outlets,
        "total_outlets_scraped": total_scraped,
        "total_success": total_success,
        "total_errors": total_errors,
        "total_menu_items": total_items,
        "finished_at": datetime.now(WIB).isoformat(),
        "areas": all_results,
    }
    summary_file.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"  Summary: {summary_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    