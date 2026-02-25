# Project Context - Scrapper GoFood

## Snapshot
- Tanggal konteks: 2026-02-25
- Area uji listing: `surabaya/sukolilo-restaurants`
- Profil uji detail: `mie-mapan-pakuwon-city-mall-0fc57cda-a004-4a16-9b43-2ff88d3c754d`
- Tujuan aktif: ekstraksi data listing + profil/menu restoran secara stabil dengan pendekatan offline-first.

## Objective Project
Pipeline ekstraksi data GoFood berbasis `__NEXT_DATA__`:
1. Ambil halaman via Playwright (JS execution + session reuse) untuk melewati challenge.
2. Ekstrak JSON dari `<script id="__NEXT_DATA__">`.
3. Parse JSON ke format terstruktur untuk use case listing restoran dan detail menu.

## Status Terkini
- `scripts/http/test_raw_html.py`:
  - Raw HTTP tanpa browser hanya mendapatkan halaman challenge (`HTTP 202`, `probe.js`).
  - Kesimpulan: pendekatan non-browser tidak cukup.
- `scripts/playwright/test_playwright_gofood.py`:
  - Berhasil ambil halaman listing dengan session/cookie management (`output/session/gofood_storage_state.json`).
  - Output HTML listing tersimpan dan `__NEXT_DATA__` terdeteksi.
- `scripts/parsers/parser_next_data.py`:
  - Berhasil ekstrak `__NEXT_DATA__` dari listing ke `output/json/gofood_next_data.json`.
- `scripts/playwright/test_profile_menu.py`:
  - Berhasil buka halaman profil restoran memakai `output/session/gofood_storage_state.json`.
  - Berhasil ekstrak `__NEXT_DATA__` ke `output/json/gofood_profile_mapan.json`.
- `scripts/playwright/test_pagination_sniffer.py`:
  - Sniffer untuk menangkap request XHR/fetch saat scroll (output ke `output/json/gofood_pagination_sniff.json`).
- `scripts/playwright/test_nearme_interceptor.py`:
  - Network interceptor untuk halaman `/near-me/` dengan infinite scroll.
  - Menangkap API responses + __NEXT_DATA__ batch awal.
  - Dynamic scroll stop (patience-based), dedup by UID.
  - Output ke `output/json/gofood_nearme_outlets.json`.
  - **Run pertama berhasil**: 135 raw entries ditangkap, 60 outlet asli setelah filtering.
  - **Fix v2**: Ditambahkan filter `CUISINE_*` (18 kategori) dan brand "General" (57 placeholder).
  - **Fix v2**: Path/URL generation via `_slugify(name)-{uid}` — divalidasi exact match terhadap path Mie Mapan.
  - Data yang tidak tersedia dari API near-me: `path` (di-generate), `image_url` (kosong).
- `scripts/batch/batch_menu_scraper.py`:
  - Batch scraper: iterasi outlet dari `gofood_nearme_outlets.json`, buka profil masing-masing, ekstrak menu.
  - Micro-batching via `--limit` dan `--offset` (default: 5 outlet per batch).
  - Polite scraping: jeda `random.uniform(3, 7)` detik antar outlet.
  - Error handling per outlet (skip + log, batch tidak crash).
  - Session di-persist setelah tiap outlet.
  - Output ke `output/json/gofood_menus_master.json`.
  - **Run pertama (batch 3)**: 3/3 success, 34 sections, 222 menu items total.
    - A&W Mall Galaxy: 14 sections, 122 items
    - Alesha Lapis Kukus Surabaya, Semolowaru: 14 sections, 60 items
    - Amanda Brownies, Mulyosari: 6 sections, 40 items

## Struktur Folder
- `scripts/`: semua skrip (http/playwright/parsers/batch)
- `output/html/`: semua HTML hasil fetch
- `output/json/`: semua JSON hasil ekstraksi
- `output/screenshots/`: screenshot Playwright
- `output/session/`: cookies + storage state Playwright

## Artefak Project
- `scripts/http/test_raw_html.py`
- `scripts/playwright/test_playwright_gofood.py`
- `scripts/playwright/test_profile_menu.py`
- `scripts/playwright/test_pagination_sniffer.py`
- `scripts/playwright/test_nearme_interceptor.py`
- `scripts/parsers/parser_next_data.py`
- `scripts/batch/batch_menu_scraper.py`
- `output/html/gofood_raw_output.html`
- `output/html/gofood_playwright_output.html`
- `output/screenshots/gofood_playwright_screenshot.png`
- `output/session/gofood_cookies.json`
- `output/session/gofood_storage_state.json`
- `output/json/gofood_next_data.json`
- `output/json/gofood_profile_mapan.json`
- `output/json/gofood_nearme_outlets.json`
- `output/json/gofood_nearme_raw_responses.json` (debug, opsional)
- `output/json/gofood_menus_master.json`

## Struktur JSON Yang Sudah Teridentifikasi

### 1) Listing Locality (`output/json/gofood_next_data.json`)
- Root: `props.pageProps.contents`
- Data outlet listing: `props.pageProps.contents[3].data[*]`
- Key penting per outlet:
  - `uid` / `core.uid` = ID outlet
  - `path` = URL path profil restoran (web)
  - `core.shortLink` = short URL
  - `ratings`, `delivery`, `priceLevel`

Contoh Mie Mapan:
- `uid`: `0fc57cda-a004-4a16-9b43-2ff88d3c754d`
- `path`: `/surabaya/restaurant/mie-mapan-pakuwon-city-mall-0fc57cda-a004-4a16-9b43-2ff88d3c754d`

### 2) Profile Restaurant (`output/json/gofood_profile_mapan.json`)
- Root page type: `"/[service_area]/restaurant/[id]"`
- Node utama outlet: `props.pageProps.outlet`
- Data profil inti: `props.pageProps.outlet.core`
- URL profil web pada JSON profile:
  - `props.pageProps.outletUrl` (bukan `outlet.path`)
- Deep-link app:
  - `props.pageProps.fallbackOpenAppURL`

Key penting:
- `outlet.uid` / `outlet.core.uid`
- `outlet.core.displayName`
- `outlet.core.shortLink`
- `outlet.delivery`
- `outlet.ratings`
- `outlet.catalog`

### 3) Struktur Menu di Halaman Profil
- Lokasi menu: `props.pageProps.outlet.catalog.sections`
- Jumlah section: `9`
- Total item menu: `82`
- Section yang terdeteksi:
  - `Resto's top picks` (0 item)
  - `ANEKA MIE` (14)
  - `Aneka Penyetan` (12)
  - `PENYETAN KOMBINASI` (17)
  - `Aneka Nasi Telur Sambal` (2)
  - `Snack Dan Gorengan` (8)
  - `TAMBAHAN` (6)
  - `MINUMAN DINGIN` (18)
  - `MINUMAN HANGAT` (5)

### 4) Near-Me Listing (via Network Interception)
- URL pattern: `https://gofood.co.id/{area}/{locality}-restaurants/near-me/`
- Data di-load via infinite scroll (lazy loading API calls saat scroll).
- Strategi: intercept JSON responses dari XHR/fetch, bukan parse HTML.
- Output: array flat outlet objects dengan uid, name, rating, delivery, dll.
- **Hasil run Sukolilo**: 60 outlet unik (dari 135 raw, setelah filter CUISINE_* dan brand General).
- API near-me **tidak menyertakan** field `path` → di-generate via `/{service_area}/restaurant/{slug}-{uid}`.
- Format slug: `_slugify(displayName)` → lowercase, non-alnum jadi dash, trim. Tervalidasi exact match.
- Entry yang difilter:
  - `CUISINE_*` (18): kategori masakan, bukan outlet (uid = `CUISINE_ANEKA_NASI`, dll.)
  - Brand General (57): placeholder brand tanpa lat/lng (uid UUID tapi tanpa `core.location`)
- Outlet asli diidentifikasi via: `core.location.latitude` != null DAN `core.location.longitude` != null.

### 5) Batch Menu Master (`output/json/gofood_menus_master.json`)
- Dihasilkan oleh `scripts/batch/batch_menu_scraper.py`.
- Array of restaurant records, masing-masing berisi:
  - `restaurant_uid`, `restaurant_name`, `restaurant_url`, `scraped_at`, `status`
  - `menu_sections[]`: array section, tiap section berisi `section_uid`, `section_name`, `section_type`, `items[]`
  - `items[]`: `item_uid`, `item_name`, `item_description`, `item_status`, `price_units`, `currency_code`, `image_url`, `variant_count`
- Record dengan `status: "error"` atau `"no_menu"` tetap disimpan untuk tracking.

## Temuan Teknis Kunci
1. `HTTP 202` tidak otomatis berarti gagal, karena Playwright tetap bisa memuat HTML penuh berisi payload data.
2. Schema listing dan schema profile berbeda, jadi extractor perlu dua parser:
   - parser listing (`contents[3].data[*]`)
   - parser profile/menu (`outlet.catalog.sections[*].items[*]`)
3. Session reuse (`storage_state`) tetap penting untuk stabilitas run terhadap WAF/challenge.
4. Ekstraksi offline dari file HTML/JSON sangat efektif untuk iterasi cepat tanpa menembak server berulang.
5. Menambahkan `near-me/` di akhir URL locality menampilkan semua restoran di lokasi tersebut (data di-load via infinite scroll).
6. API near-me mengembalikan 3 jenis objek ber-`uid`: outlet asli (punya `core.location`), brand "General" (placeholder tanpa data), dan kategori `CUISINE_*`. Hanya outlet asli yang berguna.
7. Path profil restoran mengikuti pattern `/{service_area}/restaurant/{slugified_name}-{uid}` — bisa di-generate dari displayName + uid.
8. Batch menu scraper berhasil mengekstrak menu dari 3 outlet pertama tanpa error atau blokir WAF. Schema `catalog.sections[*].items[*]` konsisten di ketiga restoran.

## Rencana Aktif (Updated)
### Phase 2A - Listing Extractor
Target output: `output/json/gofood_extracted_data.json` dari `output/json/gofood_next_data.json`.

Field minimal:
- `outlet_uid`
- `outlet_name`
- `path`
- `full_url`
- `short_link`
- `rating_average`
- `distance_km`
- `price_level`
- `is_deliverable`

### Phase 2B - Profile Menu Extractor
Target output: `output/json/gofood_profile_mapan_extracted.json` (atau CSV) dari `output/json/gofood_profile_mapan.json`.

Field minimal:
- `outlet_uid`
- `outlet_name`
- `outlet_url`
- `section_name`
- `item_uid`
- `item_name`
- `item_price_units`
- `currency_code`
- `item_status`

### Phase 3 - Join & Scale
1. Join listing output dengan profile output berdasarkan `outlet_uid`.
2. Jalankan terhadap beberapa outlet lain untuk validasi schema.
3. Tambah throttle + retry policy agar stabil.

### Phase 4 - Hardening
1. Tambah schema guard jika key/path berubah.
2. Tambah logging per run (timestamp, target URL, status, jumlah item).
3. Tambah fallback saat `__NEXT_DATA__` tidak ditemukan.

## Risiko dan Batasan
- WAF/challenge dapat berubah sewaktu-waktu.
- Struktur `__NEXT_DATA__` dapat berubah pada deploy baru.
- Perlu disiplin rate-limit dan kepatuhan Terms of Service target.

## Definition of Done (Milestone Berikutnya)
- [x] Extractor listing menghasilkan dataset outlet yang konsisten. (60 outlet via near-me interceptor)
- [x] Extractor profile menghasilkan dataset menu per item. (batch scraper, 3/3 success)
- [ ] Mapping `outlet_uid` antar listing dan profile tervalidasi.
- [x] Diuji minimal pada 2-3 outlet berbeda untuk cek ketahanan schema. (3 outlet: A&W, Alesha, Amanda)
