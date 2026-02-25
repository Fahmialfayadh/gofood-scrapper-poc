# Hasil Proof of Concept - GoFood Scrapper

## Ringkasan Eksekusi

| Metrik | Surabaya (Multi-Area, 6 kecamatan) | Medan (Selayang) |
|--------|------------------------------------|------------------|
| Locality yang dijalankan | 6 | 1 |
| Outlet ditemukan (unik) | 360 (60/area) | 60 |
| Outlet di-scrape menu | 120 (20/area) | 5 |
| Success | 117 | 5 |
| No menu | 2 | 0 |
| Error | 1 | 0 |
| Total menu sections | 1,453 | 55 |
| Total menu items | 10,340 | 331 |
| Tanggal eksekusi | 2026-02-25 | 2026-02-25 |

## Pipeline yang Dibangun

### Step 1: Session Bootstrap
- **Script**: `scripts/playwright/test_playwright_gofood.py` (atau Step 1 di `developer_test_scrapping.py`)
- **Fungsi**: Buka halaman GoFood via Playwright, lewati WAF/challenge, simpan cookies + storage state.
- **Output**: `output/session/gofood_storage_state.json`

### Step 2: Near-Me Outlet Discovery
- **Script**: `scripts/playwright/test_nearme_interceptor.py` (atau Step 2 di `developer_test_scrapping.py`)
- **Fungsi**: Buka halaman `/near-me/`, intercept API responses via Playwright network sniffing + auto-scroll.
- **Output**: `output/json/gofood_nearme_outlets.json` (atau `gofood_{locality}_outlets.json`)
- **Hasil**: 60 outlet unik per area (Sukolilo dan Medan Selayang)

### Step 3: Batch Menu Extraction (Deep-Dive)
- **Script**: `scripts/batch/batch_menu_scraper.py` (atau Step 3 di `developer_test_scrapping.py`)
- **Fungsi**: Iterasi outlet satu per satu, buka halaman profil, ekstrak `__NEXT_DATA__`, parse menu.
- **Output**: JSON + CSV (dual output)
- **Hasil Surabaya (scale test)**: 120 outlet (6 kecamatan x 20 outlet), 10,340 menu items
- **Hasil Medan**: 5 restoran, 331 menu items

### Unified Pipeline (Baru)
- **Script**: `developer_test_scrapping.py`
- **Fungsi**: Satu script menjalankan Step 1 → 2 → 3 secara otomatis.
- **Penggunaan**: `python3 developer_test_scrapping.py --area medan --locality medan-selayang-restaurants --limit 5`
- **Output**: `gofood_{locality}_outlets.json`, `gofood_{locality}_menus.json`, `gofood_{locality}_menus.csv`

### Surabaya Multi-Area Runner (Baru)
- **Script**: `scrap_sby.py`
- **Fungsi**: Menjalankan pipeline E2E untuk beberapa kecamatan Surabaya secara berurutan (dengan delay manusiawi + progress tracking).
- **Penggunaan**: `python3 scrap_sby.py --limit 20`
- **Output**:
  - Per area: `output/json/gofood_{area}_outlets.json`, `output/json/gofood_{area}_menus.json`, `output/csv/gofood_{area}_menus.csv`
  - Ringkasan: `output/json/scrap_sby_summary.json`

## Data yang Diekstrak

### Outlet Discovery (60 restoran)
Per outlet:
- `uid` (UUID unik)
- `name` (nama display)
- `full_url` (URL profil lengkap)
- `latitude`, `longitude` (koordinat)
- `rating_average` (rating GoFood)
- `delivery_distance_km`
- `price_level` (1-4)

### Menu Extraction (per restoran)
Per menu item:
- `item_uid`, `item_name`, `item_description`
- `price_units` (harga dalam IDR), `currency_code`
- `image_url` (CDN GoFood)
- `item_status` (1 = aktif)
- `variant_count` (jumlah varian/topping)

## Hasil Batch Menu (3 Restoran Pertama)
Bagian ini adalah contoh detail per-restoran. Untuk hasil skala besar, lihat section **Hasil Scale Test** dan file output di `output/json/` dan `output/csv/`.

### 1. A&W Mall Galaxy
| Section | Jumlah Item |
|---------|-------------|
| Resto's top picks | 0 |
| GOFOOD GIFTING EXCLUSIVE | 2 |
| What's New | 22 |
| FEB SUPER DEALS | 11 |
| KETO | 5 |
| 1 Orang: Paket Gratis & Kentang | 16 |
| 1 Orang: Quick & Easy | 2 |
| 2-3 Orang: Picnic Barrel | 3 |
| 4-6 Orang: Good Friends & Family | 2 |
| Chicken, Burgers, Mixbowl | 14 |
| Snacks & Sides | 20 |
| Drinks | 15 |
| Desserts | 9 |
| Others | 1 |
| **Total** | **122 items** |

### 2. Alesha Lapis Kukus Surabaya, Semolowaru
| Section | Jumlah Item |
|---------|-------------|
| Orang-orang pada doyan ini | 2 |
| Menu Banting Harga | 3 |
| Resto's top picks | 10 |
| Lapis Kukus Pahlawan | 11 |
| Almond Tart Pahlawan | 5 |
| Pia | 6 |
| Pie | 2 |
| Minuman | 1 |
| Chiffon Pahlawan | 2 |
| Bika Ambon | 1 |
| Nastar Box | 1 |
| Bolen | 2 |
| Bakpao Singosari | 10 |
| Cookies Alesha | 4 |
| **Total** | **60 items** |

### 3. Amanda Brownies, Mulyosari
| Section | Jumlah Item |
|---------|-------------|
| Orang-orang pada doyan ini | 5 |
| Resto's top picks | 0 |
| Bolu | 11 |
| Brownies | 17 |
| Snacks | 3 |
| Pastry | 4 |
| **Total** | **40 items** |

## Hasil Batch Menu — Medan Selayang (5 Restoran)

| No | Restoran | Sections | Items |
|----|----------|----------|-------|
| 1 | Aroma Bakery and Cake Shop, Sunggal | 8 | 54 |
| 2 | Aroma Bakery, Dr Mansyur | 7 | 52 |
| 3 | Asoka Corner, Ring Road | 23 | 167 |
| 4 | Ayam Geprek & Bento "PrekBen", Jl. Abdul Hakim | 13 | 37 |
| 5 | Ayam Gepuk Jogjakarta, Komplek Tasbi 2 | 4 | 21 |
| | **Total** | **55** | **331 items** |

## Hasil Scale Test — Surabaya Multi-Area (6 Kecamatan)
Sumber metrik: `output/json/scrap_sby_summary.json` (rekap outlet + items) dan agregasi `output/json/gofood_{area}_menus.json` (sections + status per outlet) untuk run 2026-02-25.

| Area | Outlet ditemukan | Outlet di-scrape | Success | No menu | Error | Sections | Items |
|------|------------------|------------------|---------|---------|-------|----------|------:|
| Sukolilo | 60 | 20 | 20 | 0 | 0 | 231 | 1,877 |
| Gubeng | 60 | 20 | 19 | 0 | 1 | 227 | 1,719 |
| Wonokromo | 60 | 20 | 19 | 1 | 0 | 209 | 1,316 |
| Tandes | 60 | 20 | 19 | 1 | 0 | 263 | 1,732 |
| Tambaksari | 60 | 20 | 20 | 0 | 0 | 255 | 1,799 |
| Mulyorejo | 60 | 20 | 20 | 0 | 0 | 268 | 1,897 |
| **Total** | **360** | **120** | **117** | **2** | **1** | **1,453** | **10,340** |

## Contoh Data Item Menu

```json
{
  "item_uid": "43f95451-1659-4ddb-9bcd-1e05128874a9",
  "item_name": "GIFTING A - 4 Aroma Chicken, Rice, Chic Chunks & RB",
  "item_description": "4 Golden/Spicy Aroma Chicken + 2 Rice + 4pcs Chicken Chunks + 2 RB Reg.",
  "item_status": 1,
  "price_units": 189500,
  "currency_code": "IDR",
  "image_url": "https://i.gojekapi.com/darkroom/gofood-indonesia/v2/images/uploads/ce46fa4e-...jpg",
  "variant_count": 3
}
```

## Strategi Anti-Blokir

1. **Session reuse**: `storage_state.json` di-load sebelum setiap navigasi, di-persist setelahnya.
2. **Anti-detection headers**: User-agent Chrome, locale `id-ID`, timezone `Asia/Jakarta`.
3. **Polite scraping**: Jeda `random(3-7)` detik antar request outlet.
4. **Micro-batching (batch scraper)**: `scripts/batch/batch_menu_scraper.py` mendukung `--limit` dan `--offset` untuk menjalankan scraping per-batch dan melanjutkan batch berikutnya.
5. **Browser flags**: `--disable-blink-features=AutomationControlled` untuk bypass bot detection.

## Filtering Logic (Near-Me Data)

Contoh pada run Sukolilo: dari 135 raw entries, 75 dibuang:
- **18 kategori `CUISINE_*`**: Bukan outlet, melainkan label kategori (uid = `CUISINE_ANEKA_NASI`, dll.)
- **57 brand "General"**: Placeholder tanpa data lokasi (e.g., "A&W General", "KFC General")
- **Indikator outlet asli**: `core.location.latitude` != null DAN `core.location.longitude` != null

## Teknologi

| Komponen | Teknologi |
|----------|-----------|
| Browser automation | Playwright (Chromium) |
| Data source | `<script id="__NEXT_DATA__">` (Next.js SSR) |
| Network interception | `page.on("response")` callback |
| Bahasa | Python 3.11+ |
| Output format | JSON + CSV (dual output) |

## File Output

| File | Deskripsi | Ukuran |
|------|-----------|--------|
| `output/session/gofood_storage_state.json` | Session Playwright | ~5 KB |
| `output/json/scrap_sby_summary.json` | Ringkasan Surabaya multi-area (6 kecamatan) | ~2 KB |
| `output/json/gofood_sukolilo-restaurants_outlets.json` | 60 outlet Sukolilo | ~40 KB |
| `output/json/gofood_sukolilo-restaurants_menus.json` | Menu 20 outlet Sukolilo | ~MB |
| `output/csv/gofood_sukolilo-restaurants_menus.csv` | CSV flat menu Sukolilo | ~MB |
| `output/json/gofood_medan-selayang-restaurants_outlets.json` | 60 outlet Medan Selayang | ~40 KB |
| `output/json/gofood_medan-selayang-restaurants_menus.json` | Menu 5 outlet (Medan) | ~200+ KB |
| `output/csv/gofood_medan-selayang-restaurants_menus.csv` | CSV flat menu (Medan) | ~150 KB |
| `output/json/gofood_menus_master.json` | Output standalone batch scraper (default 5 outlet) | ~120 KB |
| `output/csv/gofood_menus_master.csv` | CSV flat untuk `gofood_menus_master.json` | ~200 KB |

## Langkah Selanjutnya

1. ~~**Export**: Konversi ke CSV/database untuk analisis.~~ ✅ Sudah terimplementasi (dual JSON + CSV).
2. ~~**Multi-area**: Ulangi pipeline untuk area lain.~~ ✅ Sudah berjalan (Surabaya multi-kecamatan + Medan).
3. **Scale up**: Jalankan scraping untuk semua 60 outlet per locality (`--limit 60`).
4. **Join data**: Gabungkan outlet listing + menu berdasarkan `outlet_uid` untuk analisis lintas restoran.
5. **Multi-kota**: Expand ke Jakarta, Bandung, Yogyakarta, dll.
6. **Hardening**: Schema guard, retry policy, logging per run.
