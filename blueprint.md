# System Architecture & Crawler Pipeline: GoFood Scraper

Dokumen ini adalah blueprint yang menjelaskan:
1. masalah apa yang kita pecahkan,
2. kenapa pipeline ini dibangun seperti ini,
3. apa yang dilakukan setiap step,
4. input/output apa yang dihasilkan,
5. bagaimana cara menjalankan dan memvalidasi hasilnya.

Seluruh penjelasan mengacu pada kode aktual di repo ini (folder `scripts/` dan `output/`).

## Masalah Yang Dihadapi (Kenapa Butuh Playwright)
GoFood tidak selalu mengirim halaman yang sama untuk request HTTP biasa. Untuk request tanpa browser asli, server sering membalas challenge (contoh: `probe.js`) dan status seperti `202`. Artinya, kalau kita pakai "dumb bot" (requests/curl), kita tidak dapat HTML yang berisi data restoran.

Solusi yang dipakai di repo ini:
- Gunakan Playwright (Chromium) agar request terlihat seperti browser dan JS bisa dieksekusi.
- Simpan session (cookie + storage state) dan reuse untuk request berikutnya.
- Ambil data dari JSON terstruktur (bukan DOM parsing) supaya lebih tahan perubahan UI.

## Prinsip Desain
1. Offline-first analysis
   Setelah HTML/JSON tersimpan, parsing dan analisis dilakukan offline agar iterasi cepat dan tidak membebani server.
2. Hindari DOM parsing
   Kita tidak bergantung pada selector HTML/CSS. Sumber data diambil dari JSON yang sudah disediakan frontend/back-end.
3. Dua sumber data utama
   - `__NEXT_DATA__` (Next.js) yang disuntikkan di HTML hasil render.
   - JSON response XHR/fetch saat halaman melakukan infinite scroll (network interception).

## Data Flow (Gambaran Besar)
Pipeline utama bisa dibaca seperti ini:

```text
Step 1 (Bootstrap) -> output/session/gofood_storage_state.json
                        |
                        v
Step 2 (Near-me intercept + scroll) -> output/json/gofood_nearme_outlets.json
                        |
                        v
Step 3 (Batch profile scrape) -> output/json/gofood_menus_master.json
```

## Struktur Folder (Konvensi)
- `scripts/`
- `scripts/http/` untuk eksperimen HTTP tanpa browser
- `scripts/playwright/` untuk browser automation + network interception
- `scripts/parsers/` untuk ekstraksi `__NEXT_DATA__` dari HTML lokal
- `scripts/batch/` untuk batch runner (micro-batching) saat scale up
- `output/`
- `output/session/` untuk cookies + Playwright storage state
- `output/html/` untuk HTML hasil fetch/playwright
- `output/json/` untuk JSON hasil ekstraksi/intercept/batch
- `output/screenshots/` untuk screenshot debugging

## Dependency Minimum
- Python 3.10+ (union type `|` dipakai), tested di Python 3.12
- `playwright` + browser binaries (Chromium)

## Pipeline Utama (3 Step)

### Step 1: Session Bootstrap (WAF/Challenge Warm-up)
Script: `scripts/playwright/test_playwright_gofood.py`

Tujuan:
- "Memancing" WAF/challenge dengan browser asli, lalu menyimpan session supaya request berikutnya lebih stabil.

Apa yang terjadi saat script berjalan:
1. Chromium dibuka (headless default).
2. Script mengakses halaman listing GoFood (contoh: `.../sukolilo-restaurants`).
3. Script menunggu page load dan memberi waktu ekstra untuk JS render.
4. HTML disimpan (untuk inspeksi offline).
5. Cookie dan storage state disimpan (ini kunci untuk step berikutnya).

Kenapa ini penting:
- Setelah session terbentuk, Step 2 dan Step 3 bisa mengulang request tanpa "start from zero" dan risiko challenge berulang lebih kecil.
- Status HTTP bisa `202` tapi tetap ada HTML lengkap; yang penting adalah kontennya, bukan hanya status.

Output yang dihasilkan:
- `output/session/gofood_storage_state.json`
- `output/session/gofood_cookies.json`
- `output/html/gofood_playwright_output.html`
- `output/screenshots/gofood_playwright_screenshot.png`

Cara menjalankan:
```bash
.venv/bin/python scripts/playwright/test_playwright_gofood.py
```

Cara cek cepat berhasil:
1. File `output/session/gofood_storage_state.json` ada dan ukurannya masuk akal.
2. `output/html/gofood_playwright_output.html` berisi `__NEXT_DATA__`.

Parameter berguna:
- `--headful` untuk lihat browser (debug).
- `--wait-ms` untuk tambah waktu tunggu render.

### Step 2: Outlet Discovery via Near-Me (Network Interception + Auto-Scroll)
Script: `scripts/playwright/test_nearme_interceptor.py`

Tujuan:
- Mengumpulkan daftar outlet restoran sebanyak mungkin untuk sebuah locality, tanpa bergantung pada HTML listing yang biasanya memakai infinite scroll.

Kenapa near-me:
- Halaman `.../near-me/` memuat daftar restoran dengan lazy loading (infinite scroll).
- Data yang kita butuhkan sebenarnya lewat XHR/fetch. Jadi lebih efisien menangkap JSON response-nya dibanding mem-parsing DOM.

Target URL pattern:
- `https://gofood.co.id/{service_area}/{locality}-restaurants/near-me/`
- Catatan: `locality` biasanya nama kecamatan.

Apa yang dilakukan script ini (alur yang mudah diikuti):
1. Load session dari `output/session/gofood_storage_state.json`.
2. Pasang interceptor `page.on("response")` untuk semua response bertipe fetch/xhr.
3. Filter URL response pakai keyword hints (`graphql`, `api`, `search`, `outlet`, dll.) supaya tidak memproses noise.
4. Setiap JSON response di-walk secara rekursif untuk mencari objek yang bentuknya seperti outlet (punya `uid` dan `displayName`).
5. Outlet dinormalisasi jadi schema flat dan didedup berdasarkan `uid`.
6. Auto-scroll ke bawah berulang kali untuk memicu infinite scroll.
7. Berhenti otomatis dengan strategi patience-based:
   berhenti jika `patience` kali scroll berturut-turut tidak menambah outlet baru.

Filtering penting (kenapa output bukan 135 raw):
- API near-me mengandung campuran:
  - outlet asli (punya `core.location.latitude/longitude`)
  - node kategori `CUISINE_*` (bukan restoran)
  - placeholder brand "General" (tanpa koordinat)
- Script hanya menyimpan outlet asli.

Rekonstruksi URL profil (kenapa perlu generate `path`):
- API near-me sering tidak memberi `path` web profil.
- Script membangun sendiri dengan format:
  - `/{service_area}/restaurant/{slug}-{uid}`
  - slug berasal dari `_slugify(displayName)` (lowercase, non-alnum jadi `-`, trim)
- Lalu `full_url` dibentuk sebagai `https://gofood.co.id{path}`.

Output yang dihasilkan:
- `output/json/gofood_nearme_outlets.json` (array outlet flat, siap dipakai Step 3)
- `output/json/gofood_nearme_raw_responses.json` (opsional jika `--save-raw`, untuk debugging)

Cara menjalankan:
```bash
.venv/bin/python scripts/playwright/test_nearme_interceptor.py
```

Cara cek cepat berhasil:
1. `output/json/gofood_nearme_outlets.json` berupa array JSON.
2. Setiap entry punya `uid`, `name`, `full_url`, dan `latitude/longitude` tidak null.

Parameter berguna:
- `--max-scrolls` batas scroll maksimum.
- `--patience` (default 3) untuk stop lebih cepat/lebih lambat.
- `--scroll-delay` untuk kasih waktu request selesai setelah scroll.
- `--save-raw` untuk simpan semua response mentah (debug).
- `--headful` untuk melihat scroll di browser.

### Step 3: Batch Menu Extraction (Deep-Dive Profile per Outlet)
Script: `scripts/batch/batch_menu_scraper.py`

Tujuan:
- Mengambil menu lengkap per outlet (section dan items) dengan mengakses halaman profil restoran satu per satu.

Kenapa harus lewat halaman profil:
- Menu tersedia stabil di `__NEXT_DATA__` halaman profil.
- Parsing menu jadi deterministic: tinggal ambil `catalog.sections` dan `items`.

Input:
- `output/json/gofood_nearme_outlets.json`

Apa yang dilakukan script ini:
1. Baca daftar outlet (array) lalu slice sesuai `--offset` dan `--limit`.
2. Untuk setiap outlet target:
   - Buka `full_url` outlet via Playwright (session reuse).
   - Ambil HTML, ekstrak JSON dari `<script id="__NEXT_DATA__">`.
   - Parse menu dari path:
     `props.pageProps.outlet.catalog.sections[*].items[*]`
   - Simpan hasil sebagai 1 record (status bisa `success`, `no_menu`, atau `error`).
3. Persist `storage_state` setelah tiap outlet (supaya session tetap fresh).
4. Delay random antar outlet (`--delay-min` sampai `--delay-max`) untuk polite scraping.

Output:
- `output/json/gofood_menus_master.json` (array record per restoran)

Cara menjalankan (contoh batch 5 outlet pertama):
```bash
.venv/bin/python scripts/batch/batch_menu_scraper.py --limit 5 --offset 0
```

Cara menjalankan "resume":
```bash
.venv/bin/python scripts/batch/batch_menu_scraper.py --limit 5 --offset 5
```

Schema output per restoran:
- `restaurant_uid`, `restaurant_name`, `restaurant_url`, `scraped_at`, `status`
- `menu_sections[]`: `section_uid`, `section_name`, `section_type`, `items[]`
- `items[]`: `item_uid`, `item_name`, `item_description`, `item_status`, `price_units`, `currency_code`, `image_url`, `variant_count`
- Catatan: `restaurant_url` biasanya berupa path (relative) dari `outletUrl`. Jadikan full URL dengan prefix `https://gofood.co.id` bila diperlukan.

Parameter berguna:
- `--limit` dan `--offset` untuk micro-batching.
- `--wait-ms` kalau menu butuh waktu render lebih lama.
- `--headful` untuk debugging.

## Script Pendukung (Dev Tools)
- `scripts/playwright/test_profile_menu.py`
  - Ambil `__NEXT_DATA__` untuk 1 restoran target (debug schema profile).
  - Output default: `output/json/gofood_profile_mapan.json`.
- `scripts/parsers/parser_next_data.py`
  - Ekstrak `__NEXT_DATA__` dari HTML listing yang sudah tersimpan offline.
  - Input default: `output/html/gofood_playwright_output.html`
  - Output default: `output/json/gofood_next_data.json`
- `scripts/playwright/test_pagination_sniffer.py`
  - Sniff XHR/fetch saat scroll versi sederhana (lebih cocok untuk eksplorasi).
  - Output default: `output/json/gofood_pagination_sniff.json`
- `scripts/http/test_raw_html.py`
  - Baseline "dumb bot" tanpa browser untuk membuktikan challenge/WAF.

## Strategi Anti-Blokir (Yang Sudah Dipakai di Kode)
1. Session reuse
   Load dan persist `output/session/gofood_storage_state.json`.
2. Header spoofing
   Chrome UA, `locale=id-ID`, `timezone=Asia/Jakarta`.
3. Browser args
   `--disable-blink-features=AutomationControlled`.
4. Polite scraping
   Delay antar outlet pada batch scraper.

## Current PoC Status (Per 2026-02-25)
Detail lengkap ada di `result_PoC.md`. Ringkas:
- Near-me discovery: 135 raw entries -> 60 outlet valid (setelah filter)
- Batch menu: 3/3 success -> 34 sections, 222 items

## Next Action Items (Engineering)
1. Scale up batch menu sampai semua outlet di-scrape (gunakan `--offset` untuk resume).
2. Join dataset: gabungkan `gofood_nearme_outlets.json` (listing) + `gofood_menus_master.json` (menu) via `uid`.
3. Export: CSV atau load ke database untuk analisis harga/menu.
4. Hardening: schema guard + retry policy + logging run metadata.
