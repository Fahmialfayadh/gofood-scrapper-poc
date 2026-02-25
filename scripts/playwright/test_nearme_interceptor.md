# GoFood Near-Me Interceptor (`test_nearme_interceptor.py`)

## Deskripsi
Script ini menggunakan Playwright untuk melakukan intercept terhadap respons JSON API saat proses auto-scroll (infinite scroll) pada halaman `/near-me/` GoFood. Tujuannya adalah untuk mengumpulkan data semua outlet (restoran) di area tersebut.

## Strategi
1. Navigasi ke URL locality `/near-me/` GoFood.
2. Ekstrak data JSON dari tag `<script id="__NEXT_DATA__">` untuk mendapatkan batch outlet awal.
3. Memasang interceptor pada event `page.on("response")` Playwright.
4. Melakukan simulasi auto-scroll ke bawah halaman sampai tidak ada data baru yang didapat (berdasarkan kesabaran/patience).
5. Menggabungkan data outlet, melakukan deduplikasi berdasarkan UID, menormalkan data, dan menyimpannya ke dalam file JSON.

## Penggunaan

Anda dapat menjalankan script ini melalui CLI:
```bash
python scripts/playwright/test_nearme_interceptor.py [args]
```

### Argument yang Didukung:
- `--url`: URL near-me target (default: URL Sukolilo Surabaya).
- `--output`: Path untuk menyimpan hasil JSON (default: `output/json/gofood_nearme_outlets.json`).
- `--storage-state`: Path ke session Playwright untuk menjaga session/cookies (default: `output/session/gofood_storage_state.json`).
- `--headful`: Mengaktifkan mode visual browser (non-headless).
- `--max-scrolls`: Batas maksimum jumlah scroll otomatis (default: 100).
- `--patience`: Jumlah scroll tanpa data baru yang ditoleransi sebelum skrip berhenti (default: 3).
- `--scroll-delay`: Detik jeda setelah tiap scroll (default: 2.5).
- `--save-raw`: Jika diset, akan menyimpan raw API response ke file terpisah.
- `--wait-ms`: Waktu tunggu usai initial page load (default: 5000 ms).
