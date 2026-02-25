# GoFood Scraper PoC

Proof-of-concept pipeline untuk ekstraksi data restoran dan menu dari GoFood menggunakan **Playwright** (browser automation) dan parsing `__NEXT_DATA__` (Next.js SSR payload).

## Highlights

| Metrik | Nilai |
|--------|-------|
| Area tervalidasi | Surabaya (Sukolilo), Medan (Selayang) |
| Outlet ditemukan per area | 60 |
| Success rate scraping menu | **100%** (8/8 outlet) |
| Total menu items diekstrak | 553 |
| Output format | JSON + CSV |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Jalankan pipeline (satu perintah)
python3 developer_test_scrapping.py \
  --area surabaya \
  --locality sukolilo-restaurants \
  --limit 5
```

Output otomatis tersimpan di `output/`:
- `output/json/gofood_sukolilo-restaurants_outlets.json` — daftar outlet
- `output/json/gofood_sukolilo-restaurants_menus.json` — menu (nested JSON)
- `output/csv/gofood_sukolilo-restaurants_menus.csv` — menu (flat CSV, siap Excel)

### Parameter Utama

| Argumen | Fungsi | Contoh |
|---------|--------|--------|
| `--area` | Kota / service area | `surabaya`, `medan`, `jakarta` |
| `--locality` | Kecamatan | `sukolilo-restaurants`, `gubeng-restaurants` |
| `--limit` | Jumlah outlet yang di-scrape menunya | `5`, `10`, `60` |
| `--headful` | Tampilkan browser (debug/captcha) | — |

---

## 📖 Panduan Baca Dokumentasi

Baca file-file berikut **secara berurutan** untuk memahami project dari gambaran besar hingga detail teknis:

### 1️⃣ Gambaran Besar & Arsitektur
> *Mulai dari sini untuk memahami "kenapa" dan "bagaimana" pipeline ini dibangun.*

- **[blueprint.md](blueprint.md)** — Arsitektur sistem, prinsip desain, data flow, dan penjelasan lengkap tiap step pipeline beserta cara menjalankannya.

### 2️⃣ Laporan Non-Teknis
> *Penjelasan pipeline dalam bahasa yang mudah dimengerti (cocok untuk presentasi).*

- **[Laporan_Pipeline_Scraping_GoFood.md](Laporan_Pipeline_Scraping_GoFood.md)** — Laporan naratif: konsep dasar, alur kerja per tahap, bentuk data yang ditambang, dan strategi anti-blokir.

### 3️⃣ Hasil & Bukti PoC
> *Data kuantitatif: berapa outlet, berapa menu, tabel rinci per restoran.*

- **[result_PoC.md](result_PoC.md)** — Ringkasan eksekusi (Surabaya + Medan), detail hasil per restoran, contoh data JSON, filtering logic, dan langkah selanjutnya.

### 4️⃣ Konteks Teknis Project
> *"Living document" — catatan teknis internal yang selalu di-update.*

- **[context.md](context.md)** — Status terkini tiap script, struktur JSON yang sudah teridentifikasi, temuan teknis kunci, rencana aktif, dan definition of done.

### 5️⃣ Detail Script Playwright
> *Deep-dive per script: alur internal, diagram, dan relasi antar script.*

- **[scripts/playwright/playwright-flow.md](scripts/playwright/playwright-flow.md)** — Diagram Mermaid + penjelasan alur kerja keempat script Playwright dan hubungannya dalam pipeline.

Dokumentasi per-script (opsional, untuk referensi cepat):
- [test_playwright_gofood.md](scripts/playwright/test_playwright_gofood.md) — Session bootstrap & skenario klasifikasi
- [test_nearme_interceptor.md](scripts/playwright/test_nearme_interceptor.md) — Outlet discovery via network interception
- [test_pagination_sniffer.md](scripts/playwright/test_pagination_sniffer.md) — API pagination sniffer (eksplorasi)
- [test_profile_menu.md](scripts/playwright/test_profile_menu.md) — Single profile menu extractor

---

## Struktur Project

```
├── developer_test_scrapping.py    # ⭐ Unified E2E pipeline (one-command)
├── requirements.txt
├── blueprint.md                   # Arsitektur & panduan teknis
├── context.md                     # Living doc status project
├── result_PoC.md                  # Hasil PoC kuantitatif
├── Laporan_Pipeline_Scraping_GoFood.md
│
├── scripts/
│   ├── playwright/                # Browser automation scripts
│   │   ├── test_playwright_gofood.py      # Step 1: Session bootstrap
│   │   ├── test_nearme_interceptor.py     # Step 2: Outlet discovery
│   │   ├── test_profile_menu.py           # Single profile extractor
│   │   ├── test_pagination_sniffer.py     # API sniffer (riset)
│   │   └── playwright-flow.md             # Flow documentation
│   ├── batch/
│   │   └── batch_menu_scraper.py          # Step 3: Batch menu extraction
│   ├── parsers/
│   │   └── parser_next_data.py            # Offline JSON parser
│   └── http/
│       └── test_raw_html.py               # Baseline HTTP test
│
└── output/
    ├── json/          # JSON hasil ekstraksi
    ├── csv/           # CSV flat (dual output)
    ├── session/       # Cookies & storage state
    ├── html/          # HTML mentah
    └── screenshots/   # Screenshot debugging
```

## Teknologi

| Komponen | Stack |
|----------|-------|
| Browser automation | Playwright (Chromium) |
| Data source | `<script id="__NEXT_DATA__">` + XHR interception |
| Bahasa | Python 3.11+ |
| Output | JSON + CSV |
