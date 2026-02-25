# Playwright GoFood State Tester (`test_playwright_gofood.py`)

## Deskripsi
Script ini merupakan script debugging dan observasi untuk menguji bagaimana website GoFood bereaksi terhadap kunjungan bot dari Playwright. Script ini akan mengklasifikasikan respons server GoFood ke dalam beberapa skenario pertahanan atau struktur loading.

## Skenario Klasifikasi
- **A (Jackpot - SSR Rendered)**: Server side rendering sepenuhnya (outlet name bisa ditemukan).
- **B (Next.js State)**: Data outlet dikirim via `<script id="__NEXT_DATA__">`.
- **C (The Wall - Anti Bot)**: Terkena pemblokiran anti-bot seperti Cloudflare atau status code 202/403.
- **D (Empty Skeleton / strict CSR)**: Halaman hanya menampilkan komponen skeleton dan bergantung murni pada load client-side.

## Cara Kerja
1. Playwright membuka URL restoran/listing target.
2. Melakukan injeksi user-agent.
3. Mencoba menggunakan (atau membuat) file session/cookies lama via `--storage-state`.
4. Mengekstrak dan memilah `__NEXT_DATA__` dari HTML jika ditemukan.
5. Menyimpan segala state dari testing (HTML, Screenshot, Cookie, dan Local Storage).

## Penggunaan

```bash
python scripts/playwright/test_playwright_gofood.py [args]
```

### Argument yang Didukung:
- `--url`: URL dari GoFood target.
- `--headful`: Mengaktifkan mode visual browser (non-headless).
- `--wait-ms`: Waktu tunggu (delay idle) usai load (default: 12000 ms).
