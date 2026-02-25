# Hasil Proof of Concept - GoFood Scrapper

## Ringkasan Eksekusi

| Metrik | Nilai |
|--------|-------|
| Area target | Surabaya / Sukolilo |
| Total outlet terdeteksi (raw) | 135 |
| Outlet valid setelah filter | 60 |
| Outlet di-scrape menu (batch 1) | 3 |
| Success rate | 3/3 (100%) |
| Total menu sections | 34 |
| Total menu items | 222 |
| Tanggal eksekusi | 2026-02-25 |

## Pipeline yang Dibangun

### Step 1: Session Bootstrap
- **Script**: `scripts/playwright/test_playwright_gofood.py`
- **Fungsi**: Buka halaman GoFood via Playwright, lewati WAF/challenge, simpan cookies + storage state.
- **Output**: `output/session/gofood_storage_state.json`

### Step 2: Near-Me Outlet Discovery
- **Script**: `scripts/playwright/test_nearme_interceptor.py`
- **Fungsi**: Buka halaman `/near-me/`, intercept API responses via Playwright network sniffing + auto-scroll.
- **Output**: `output/json/gofood_nearme_outlets.json`
- **Hasil**: 60 outlet unik dari area Sukolilo

### Step 3: Batch Menu Extraction (Deep-Dive)
- **Script**: `scripts/batch/batch_menu_scraper.py`
- **Fungsi**: Iterasi outlet satu per satu, buka halaman profil, ekstrak `__NEXT_DATA__`, parse menu.
- **Output**: `output/json/gofood_menus_master.json`
- **Hasil**: 3 restoran, 222 menu items

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
4. **Micro-batching**: Default 5 outlet per run, bisa diatur via `--limit` dan `--offset`.
5. **Browser flags**: `--disable-blink-features=AutomationControlled` untuk bypass bot detection.

## Filtering Logic (Near-Me Data)

Dari 135 raw entries, 75 dibuang:
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
| Output format | JSON |

## File Output

| File | Deskripsi | Ukuran |
|------|-----------|--------|
| `output/json/gofood_nearme_outlets.json` | 60 outlet Sukolilo | ~41 KB |
| `output/json/gofood_menus_master.json` | Menu 3 restoran | ~200+ KB |
| `output/session/gofood_storage_state.json` | Session Playwright | ~5 KB |

## Langkah Selanjutnya

1. **Scale up**: Jalankan batch scraper untuk semua 60 outlet (`--limit 60`).
2. **Join data**: Gabungkan outlet listing + menu berdasarkan `outlet_uid`.
3. **Export**: Konversi ke CSV/database untuk analisis.
4. **Multi-area**: Ulangi pipeline untuk area lain (e.g., `gubeng-restaurants`, `tegalsari-restaurants`).
5. **Hardening**: Schema guard, retry policy, logging per run.
