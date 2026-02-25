# Project Context - Scrapper GoFood

## Snapshot
- Tanggal konteks: 2026-02-25 (updated)
- Area tervalidasi:
  - Surabaya: `sukolilo-restaurants`, `gubeng-restaurants`, `wonokromo-restaurants`, `tandes-restaurants`, `tambaksari-restaurants`, `mulyorejo-restaurants`
  - Medan: `medan-selayang-restaurants`
- Fokus: ekstraksi outlet + menu GoFood dengan Playwright, berbasis JSON (`__NEXT_DATA__` dan network interception).

### Hasil Run Terakhir (Empiris)
- Surabaya multi-area (`scrap_sby.py`, limit=20 per area):
  - 6 area, `360` outlet ditemukan (60/area), `120` outlet di-scrape menu
  - `117` success, `2` no_menu, `1` error
  - `10,340` menu items total
  - Summary: `output/json/scrap_sby_summary.json`
- Medan Selayang (`developer_test_scrapping.py`, limit=5):
  - `60` outlet ditemukan, `5` outlet di-scrape menu
  - `5` success
  - `331` menu items total
  - Output: `output/json/gofood_medan-selayang-restaurants_menus.json`

## Objective Project
Membangun pipeline ekstraksi data GoFood yang:
1. Bisa melewati WAF/challenge (session reuse via Playwright).
2. Tidak rapuh terhadap perubahan UI (hindari DOM parsing).
3. Menghasilkan dataset outlet + menu dalam JSON (nested) dan CSV (flat).

## Struktur Folder
- `scripts/`: semua skrip
- `scripts/http/`: eksperimen HTTP tanpa browser
- `scripts/playwright/`: browser automation + network interception
- `scripts/parsers/`: ekstraksi `__NEXT_DATA__` dari HTML offline
- `scripts/batch/`: batch runner untuk scraping menu
- `output/html/`: HTML hasil fetch/playwright
- `output/json/`: JSON hasil ekstraksi/intercept
- `output/csv/`: CSV flat hasil ekstraksi menu
- `output/session/`: cookies + Playwright storage state
- `output/screenshots/`: screenshot debugging

## Script Utama (Yang Dipakai Saat Ini)

### 1) Session Bootstrap
- Script: `scripts/playwright/test_playwright_gofood.py`
- Fungsi: warm-up session agar request berikutnya stabil (walaupun HTTP bisa `202`).
- Output penting:
  - `output/session/gofood_storage_state.json`
  - `output/session/gofood_cookies.json`
  - `output/html/gofood_playwright_output.html`

### 2) Outlet Discovery (Near-Me Interceptor)
- Script: `scripts/playwright/test_nearme_interceptor.py`
- Fungsi: buka halaman `.../near-me/`, auto-scroll, intercept JSON response fetch/xhr, dedup outlet by `uid`.
- Output: `output/json/gofood_nearme_outlets.json` (atau output per locality via pipeline E2E).

### 3) Batch Menu Scraper (Standalone)
- Script: `scripts/batch/batch_menu_scraper.py`
- Input: `output/json/gofood_nearme_outlets.json`
- Output (dual):
  - `output/json/gofood_menus_master.json`
  - `output/csv/gofood_menus_master.csv`
- Kondisi output saat ini (berdasarkan file di `output/`): 5 restoran, 64 sections, 419 items.

### 4) Unified E2E Pipeline (Single Locality)
- Script: `developer_test_scrapping.py`
- Fungsi: Step 1 (bootstrap) → Step 2 (discover) → Step 3 (menu) dalam satu run.
- Output di-*namespace* per locality:
  - `output/json/gofood_{locality}_outlets.json`
  - `output/json/gofood_{locality}_menus.json`
  - `output/csv/gofood_{locality}_menus.csv`

### 5) Surabaya Multi-Area Runner
- Script: `scrap_sby.py`
- Fungsi: jalankan pipeline E2E untuk daftar kecamatan Surabaya secara berurutan dengan delay manusiawi + progress tracking.
- Output:
  - Per area: `output/json/gofood_{area}_outlets.json`, `output/json/gofood_{area}_menus.json`, `output/csv/gofood_{area}_menus.csv`
  - Progress: `output/json/scrap_sby_progress.json`
  - Summary final: `output/json/scrap_sby_summary.json`

## Struktur Data (Schema Yang Stabil)

### A) Outlet Listing (hasil near-me interceptor)
File contoh: `output/json/gofood_sukolilo-restaurants_outlets.json`

Key utama per outlet:
- `uid`, `name`
- `path` + `full_url` (kadang di-generate via slugify jika API tidak memberi `path`)
- `latitude`, `longitude`
- `rating_average`, `rating_total`
- `delivery_distance_km`, `price_level`, `status`

Filtering yang diterapkan:
- Buang `CUISINE_*` (kategori, bukan outlet)
- Buang placeholder brand "General" (tidak punya `core.location`)

### B) Menu (hasil profile scraping)
File contoh: `output/json/gofood_sukolilo-restaurants_menus.json`

Per restoran:
- `restaurant_uid`, `restaurant_name`, `restaurant_url`, `scraped_at`, `status`
- `menu_sections[]`

Per section:
- `section_uid`, `section_name`, `section_type`, `items[]`

Per item:
- `item_uid`, `item_name`, `item_description`, `item_status`
- `price_units`, `currency_code`, `image_url`, `variant_count`

### C) CSV Flat (siap Excel / BI)
File contoh: `output/csv/gofood_sukolilo-restaurants_menus.csv`

Catatan penting:
- CSV di-flatten per item, tetapi record `error`/`no_menu` tetap ditulis minimal 1 baris (tracking).
- Section tanpa item juga muncul 1 baris (tracking), sehingga jumlah baris CSV tidak selalu sama dengan jumlah items.

## Temuan Teknis Kunci
1. `HTTP 202` tidak otomatis berarti gagal; yang penting adalah HTML penuh + `__NEXT_DATA__` berhasil didapat via Playwright.
2. Near-me discovery lebih stabil jika mengambil data dari network response daripada parsing HTML listing.
3. API near-me tidak selalu memberi `path`, jadi `path/full_url` perlu fallback generator: `/{area}/restaurant/{slug}-{uid}`.
4. Skala 120 outlet (6 area Surabaya, 20 outlet/area) bisa dilakukan tanpa crash: output tetap tersimpan, error/no_menu ter-track.

## Rencana Lanjutan
1. Scale up ke `--limit 60` per locality (full coverage 60 outlet/area yang ditemukan near-me).
2. Tambah retry/backoff untuk error outlet (mis. timeout sementara).
3. Join dataset lintas area (Surabaya) untuk analisis agregat (harga/menu per brand, clustering wilayah, dsb).
4. Multi-kota: perluas ke kota lain (Jakarta, Bandung, Yogyakarta) dengan pola yang sama.
