# GoFood Pagination Sniffer (`test_pagination_sniffer.py`)

## Deskripsi
Script ini berfungsi sebagai alat penyadap jalur komunikasi (sniffer) API pada fungsi pagination/infinite scroll di GoFood. Script ini memaksa Playwright untuk scroll tiga kali dan memantau (intercept) `page.on("response")` dari request tipe `fetch` atau `xhr`.

## Fitur Utama
- Menyadap URL yang memiliki keyword API (`graphql`, `api`, `search`).
- Menyimpan payload request (`post_data`) yang berguna untuk memahami mekanisme parameter `cursor` atau `page`.
- Menyimpan JSON response utuh dari API tersebut.

## Penggunaan

Jalankan script menggunakan:
```bash
python scripts/playwright/test_pagination_sniffer.py
```

### Output
Hasil dari sadapan akan dicatat secara otomatis ke `output/json/gofood_pagination_sniff.json`. File tersebut berisi:
- `url` API yang tertangkap
- `method` HTTP
- `post_data` untuk melihat parameter payload yang digunakan untuk load data
- `response` raw JSON
