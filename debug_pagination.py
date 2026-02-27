"""
Debug: cek berapa outlet yang GoFood kirim di __NEXT_DATA__
dan apakah ada info pagination (hasMore, total, cursor, dll).

Usage:
  python3 debug_pagination.py
  python3 debug_pagination.py --headful
"""

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from developer_test_scrapping import (
    BROWSER_ARGS,
    OUTPUT_DIR,
    _context_kwargs,
    _extract_outlets_recursive,
    step1_session_bootstrap,
)

CITY = "surabaya"
# Test beberapa area dengan kepadatan berbeda
TEST_AREAS = [
    "lakarsantri-restaurants",
    "gubeng-restaurants",
    "tambaksari-restaurants",
]

PAGINATION_KEYWORDS = [
    "total", "count", "hasmore", "hasnext", "cursor", "nextpage",
    "offset", "pagesize", "perpage", "limit", "paging", "pagination",
    "pageinfo", "lastpage", "nexttoken",
]

NEXT_DATA_RE = re.compile(
    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def find_pagination_hints(node, path="root", depth=0) -> list[dict]:
    """Cari key yang berhubungan dengan pagination."""
    if depth > 8:
        return []
    hints = []
    if isinstance(node, dict):
        for k, v in node.items():
            k_lower = k.lower()
            if any(kw in k_lower for kw in PAGINATION_KEYWORDS):
                val_preview = str(v)
                if len(val_preview) > 150:
                    val_preview = val_preview[:150] + "..."
                hints.append({"path": f"{path}.{k}", "key": k, "value": val_preview})
            if isinstance(v, (dict, list)):
                hints.extend(find_pagination_hints(v, f"{path}.{k}", depth + 1))
    elif isinstance(node, list):
        for i, item in enumerate(node[:5]):  # cek 5 item pertama aja
            if isinstance(item, (dict, list)):
                hints.extend(find_pagination_hints(item, f"{path}[{i}]", depth + 1))
    return hints


def analyze_area(browser, area: str, storage_state: Path):
    nearme_url = f"https://gofood.co.id/{CITY}/{area}/near-me/"
    listing_url = f"https://gofood.co.id/{CITY}/{area}"
    label = area.replace("-restaurants", "").replace("-", " ").title()

    print(f"\n{'='*60}")
    print(f"  🔍 Analyzing: {label}")
    print(f"{'='*60}")

    # Bootstrap
    ok = step1_session_bootstrap(browser, listing_url, storage_state, 8000)
    if not ok:
        print("  ❌ Bootstrap gagal")
        return None

    # Load near-me
    context = browser.new_context(**_context_kwargs(storage_state))
    page = context.new_page()
    page.goto(nearme_url, wait_until="domcontentloaded", timeout=60_000)
    try:
        page.wait_for_load_state("networkidle", timeout=20_000)
    except PlaywrightTimeoutError:
        pass
    page.wait_for_timeout(8000)

    html = page.content()
    context.close()

    # Parse __NEXT_DATA__
    match = NEXT_DATA_RE.search(html)
    if not match:
        print("  ❌ __NEXT_DATA__ tidak ditemukan!")
        return None

    payload = json.loads(match.group(1).strip())
    page_props = payload.get("props", {}).get("pageProps", {})
    contents = page_props.get("contents", [])

    # Hitung outlet
    all_outlets = _extract_outlets_recursive(payload)
    unique_uids = {o.get("uid") for o in all_outlets if o.get("uid")}

    print(f"\n  📊 Hasil __NEXT_DATA__:")
    print(f"     Total outlet raw     : {len(all_outlets)}")
    print(f"     Outlet unik (by uid) : {len(unique_uids)}")
    print(f"     Jumlah 'contents' sections: {len(contents)}")

    # Detail per section
    print(f"\n  📦 Breakdown per section:")
    for i, section in enumerate(contents):
        if not isinstance(section, dict):
            continue
        stype = section.get("type", "?")
        stitle = section.get("title", section.get("sectionTitle", "?"))
        data = section.get("data", [])
        data_count = len(data) if isinstance(data, list) else 0

        # Hitung outlet dalam section ini
        section_outlets = _extract_outlets_recursive(section)
        print(f"     [{i}] type={stype!r:30s} title={str(stitle)[:30]:30s} "
              f"data_items={data_count:3d}  outlets={len(section_outlets)}")

    # Cari pagination hints
    print(f"\n  🔎 Pagination hints di __NEXT_DATA__:")
    hints = find_pagination_hints(payload)
    if hints:
        for h in hints:
            print(f"     {h['path']}")
            print(f"       {h['key']} = {h['value']}")
    else:
        print(f"     ❌ TIDAK ADA pagination hints sama sekali")
        print(f"     → GoFood TIDAK mengirim info total/hasMore/cursor")
        print(f"     → {len(unique_uids)} outlet = semua yang tersedia untuk area ini")

    # Cek pageProps level keys
    print(f"\n  🔑 pageProps top-level keys: {list(page_props.keys())}")

    return {
        "area": area,
        "label": label,
        "total_outlets_raw": len(all_outlets),
        "unique_outlets": len(unique_uids),
        "sections": len(contents),
        "pagination_hints": hints,
        "pageProps_keys": list(page_props.keys()),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--headful", action="store_true")
    args = parser.parse_args()

    storage_state = OUTPUT_DIR / "session" / "gofood_storage_state.json"
    storage_state.parent.mkdir(parents=True, exist_ok=True)

    results = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headful, args=BROWSER_ARGS)

        for area in TEST_AREAS:
            r = analyze_area(browser, area, storage_state)
            if r:
                results.append(r)

        browser.close()

    # Summary
    print(f"\n\n{'='*60}")
    print(f"  📋 KESIMPULAN")
    print(f"{'='*60}")
    for r in results:
        has_pagination = "✅ Ada" if r["pagination_hints"] else "❌ Tidak ada"
        print(f"  {r['label']:20s}: {r['unique_outlets']:3d} outlet | Pagination: {has_pagination}")

    if all(not r["pagination_hints"] for r in results):
        print(f"\n  💡 KESIMPULAN: GoFood TIDAK punya pagination di near-me page.")
        print(f"     Semua data dikirim sekaligus di __NEXT_DATA__ (SSR).")
        print(f"     ~60 outlet per area = LIMIT SERVER, bukan bug script.")
    else:
        print(f"\n  ⚠️  Ada pagination hints! Mungkin bisa fetch lebih banyak data.")

    dump_file = OUTPUT_DIR / "json" / "debug_pagination.json"
    dump_file.parent.mkdir(parents=True, exist_ok=True)
    dump_file.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"\n  Detail: {dump_file}")


if __name__ == "__main__":
    main()
