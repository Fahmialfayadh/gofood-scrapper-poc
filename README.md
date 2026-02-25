# GoFood Scraper PoC

Proof-of-concept pipeline untuk ekstraksi data restoran dan menu dari GoFood menggunakan **Playwright** (browser automation) + JSON extraction (Next.js `__NEXT_DATA__` dan network interception saat infinite scroll).

## Status PoC (Latest)

| Run | Outlet ditemukan | Outlet di-scrape | Success | No menu | Error | Menu items |
|-----|------------------|------------------|---------|---------|-------|-----------:|
| Surabaya multi-area (6 kecamatan, limit=20/area) | 360 (60/area) | 120 | 117 | 2 | 1 | 10,340 |
| Medan Selayang (limit=5) | 60 | 5 | 5 | 0 | 0 | 331 |

Output tersedia dalam dua format:
- JSON nested (restoran → section → item) di `output/json/`
- CSV flat (1 baris = item, dengan context restoran+section) di `output/csv/`

## Quick Start

```bash
# 1) Setup (disarankan pakai virtualenv)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium

# 2a) Single locality (one-command)
.venv/bin/python developer_test_scrapping.py --area surabaya --locality sukolilo-restaurants --limit 5

# 2b) Surabaya multi-area (6 kecamatan, per-area output + summary)
.venv/bin/python scrap_sby.py --limit 20
```

Output utama:
- Per locality:
  - `output/json/gofood_{locality}_outlets.json`
  - `output/json/gofood_{locality}_menus.json`
  - `output/csv/gofood_{locality}_menus.csv`
- Multi-area Surabaya:
  - `output/json/scrap_sby_progress.json` (progress untuk resume)
  - `output/json/scrap_sby_summary.json` (rekap akhir)

## Dokumentasi
- `blueprint.md` — arsitektur + penjelasan step-by-step pipeline
- `Laporan_Pipeline_Scraping_GoFood.md` — laporan naratif (bahasa non-teknis)
- `result_PoC.md` — hasil PoC + tabel metrik
- `context.md` — catatan teknis hidup (status script, schema, hasil run terbaru)

## Struktur Project

```
├── developer_test_scrapping.py    # Unified E2E pipeline (single locality)
├── scrap_sby.py                   # Surabaya multi-area runner (6 kecamatan)
├── requirements.txt
├── blueprint.md
├── context.md
├── result_PoC.md
├── Laporan_Pipeline_Scraping_GoFood.md
│
├── scripts/
│   ├── playwright/
│   │   ├── test_playwright_gofood.py      # Session bootstrap (manual/debug)
│   │   ├── test_nearme_interceptor.py     # Near-me discovery (manual/debug)
│   │   ├── test_profile_menu.py           # Single profile extractor (debug)
│   │   └── test_pagination_sniffer.py     # Network sniffer (eksplorasi)
│   ├── batch/
│   │   └── batch_menu_scraper.py          # Batch menu scraper (standalone)
│   ├── parsers/
│   │   └── parser_next_data.py            # Offline __NEXT_DATA__ extractor
│   └── http/
│       └── test_raw_html.py               # Baseline dumb-bot HTTP test
│
└── output/
    ├── json/
    ├── csv/
    ├── session/
    ├── html/
    └── screenshots/
```
