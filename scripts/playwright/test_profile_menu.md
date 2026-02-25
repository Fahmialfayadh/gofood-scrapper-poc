# Profile Menu Extractor (`test_profile_menu.py`)

## Deskripsi
Script ini menggunakan Playwright untuk membuka halaman profil spesifik dari sub-link restoran di GoFood, dan secara eksplisit mencari kemudian mengambil (ekstraksi) data JSON yang disematkan dalam tag script HTML `<script id="__NEXT_DATA__">`.

Data `__NEXT_DATA__` tersebut memuat struktur restoran dan seluruh isi menu yang ditawarkan oleh restoran.

## Proses Utama
1. Membuka _browser context_ baru tanpa anti-bot detection strict (Playwright dengan headful/headless).
2. Mengecek apakah terdapat resume sesi/cookie dalam file `storage_state.json`.
3. Membuka URL restoran dan menunggu hingga `networkidle`.
4. Mendownload dan memilah HTML response untuk menangkap script block `__NEXT_DATA__`.
5. Mendecode teks ke dalam obyek JSON dan menyimpannya di file.

## Penggunaan

```bash
python scripts/playwright/test_profile_menu.py [args]
```

### Argument yang Didukung:
- `--url`: URL halaman detail profil resto GoFood.
- `--output`: File destinasi untuk menyimpan JSON hasil parse dari tag `__NEXT_DATA__` (default: `output/json/gofood_profile_mapan.json`).
- `--storage-state`: Path storage/cookie browser untuk persistence login antarsesi (default: `output/session/gofood_storage_state.json`).
- `--wait-ms`: Jeda tunggu tambahan setelah request utama berhasil (default: 12000 ms).
- `--headful`: Mode visual (non-headless) untuk memantau navigasi browser.
