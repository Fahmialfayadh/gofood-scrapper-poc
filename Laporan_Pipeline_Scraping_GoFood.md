# Laporan Ekstensif: Pipeline Scraping Data GoFood

## Pendahuluan
Laporan ini menjelaskan secara detail bagaimana sistem ekstraksi otomatis (*scraper*) untuk data GoFood dirancang dan bekerja. Mengingat GoFood memiliki sistem pertahanan bot yang kuat, pengambilan data tidak bisa dilakukan dengan request HTTP biasa. Laporan ini akan membahas setiap langkah, peran skrip yang dibuat, wujud data yang dihasilkan (*output*), dan bagaimana data tersebut diproses di tahap selanjutnya.

---

## 🏗️ Konsep Dasar & Framework
Aplikasi web GoFood dibangun menggunakan framework **Next.js**. Ini berarti data-data penting (daftar restoran, profil, dan menu) tidak dirender langsung sebagai teks HTML biasa, melainkan disematkan dalam bentuk data JSON penuh di dalam tag khusus `<script id="__NEXT_DATA__">`.

Untuk menghalangi bot otomatis, GoFood menggunakan WAF (*Web Application Firewall*) seperti Cloudflare. Jika kita menggunakan *scraper* biasa tanpa peramban (seperti `curl` atau `requests` di Python), kita hanya akan mendapatkan halaman blokir (HTTP 202 atau 403) yang meminta verifikasi *Captcha*. 

Oleh karena itu, sistem ini menggunakan **Playwright** (sebuah pustaka pembuka peramban otomatis) untuk meniru perilaku manusia seutuhnya—memuat halaman lewat Chrome sungguhan, menyimpan *cookies*, mengeksekusi *JavaScript*, dan melakukan *scroll*.

Pipeline utama dibagi menjadi tiga tahap:
1. **Session Bootstrap** (Mendapatkan "Tiket Masuk")
2. **Outlet Discovery** (Mencari dan Menemukan Restoran)
3. **Batch Menu Extraction** (Mengekstrak Katalog Menu secara Massal)

---

## 🚀 Alur Kerja per Tahap (Pipeline)

### Tahap 1: Mendapatkan "Tiket Masuk" (Session Bootstrap)
**Tujuan:** Menembus pertahanan awal GoFood dan menyimpan identitas sesi agar dianggap sebagai pengunjung manusia asli.
- **Skrip:** `scripts/playwright/test_playwright_gofood.py`
- **Cara Kerja:** Skrip membuka browser Chrome otomatis, mengakses halaman GoFood, dan menunggu hingga seluruh proses periksa keamanan (*antibot check*) selesai. Setelah berhasil masuk ke halaman utama, skrip **menyimpan status sesi** (yakni *cookie* dan *Local Storage* browser).
- **Penyimpanan Output:** `output/session/gofood_storage_state.json`
- **Tindak Lanjut Output:** File konfigurasi `.json` ini sangat krusial. File ini akan "disuntikkan" ke semua skrip pada Tahap 2 dan 3, sehingga setiap kali kita membuka halaman restoran baru, kita tidak dicurigai sebagai pengunjung tak dikenal, melainkan pengunjung lama yang sudah terverifikasi.

### Tahap 2: Menemukan Restoran Sekitar (Near-Me Outlet Discovery)
**Tujuan:** Mengumpulkan seluruh daftar restoran di suatu area (misal: Sukolilo) tanpa melakukan klik manual.
- **Skrip:** `scripts/playwright/test_nearme_interceptor.py`
- **Cara Kerja:** Skrip ini membuka halaman direktori area `/near-me/`. Di GoFood, daftar restoran dimuat sedikit demi sedikit saat pengguna men-*scroll* layar (*infinite scroll*). Skrip ini memalsukan gerakan *scroll* ke bawah secara berkala sambil memantau (menyadap/*intercept*) jalur komunikasi API di latar belakang. Saat *server* mengirim balasan (*response*) JSON berisi restoran baru, skrip mencegat dan mengambilnya.
- **Penyaringan (Filtering):** Data mentah yang disadap cukup kotor (ditemukan 135 *entry*). Skrip menjalankan filter berlapis: membuang data berupa Kategori Masakan (contoh: ID `CUISINE_ANEKA_NASI`) dan membuang merk tanpa titik koordinat (contoh: "KFC General"). Hasil akhirnya didapatkan **60 outlet valid**.
- **Penyimpanan Output:** `output/json/gofood_nearme_outlets.json`
- **Tindak Lanjut Output:** File ini berisi daftar riwayat 60 restoran beserta koordinat lengkapnya. File ini akan dibaca oleh skrip di Tahap 3 sebagai "Daftar Tugas" (*queue*) restoran mana saja yang harus dikunjungi untuk diambil menunya.

### Tahap 3: Panen Katalog Menu (Batch Menu Extraction)
**Tujuan:** Mengunjungi setiap profil restoran yang dikumpulkan di Tahap 2 dan menambang data menunya secara mendalam.
- **Skrip:** `scripts/batch/batch_menu_scraper.py`
- **Cara Kerja:** Skrip membaca daftar 60 restoran tadi. Memanfaatkan "tiket" sesi dari Tahap 1, skrip akan berkeliling:
  1. Membuka URL web profil Restoran A.
  2. Sama sekali tidak mempedulikan tampilan visualnya, skrip mengekstrak data dari `<script id="__NEXT_DATA__">` yang tersimpan di barisan kode HTML.
  3. Mengurai data JSON tersebut untuk mendapatkan semua kategori, nama menu, beserta harganya.
  4. Beristirahat secara acak (3-7 detik) meniru jeda manusia pindah halaman.
  5. Pindah ke Restoran B, C,... hingga batas harian tercapai. Skrip berjalan berkelompok kecil (5 resto berturut-turut lalu menyimpan hasil sementara).
- **Penyimpanan Output:** `output/json/gofood_menus_master.json`
- **Tindak Lanjut Output:** File ini adalah data master (berisi struktur ratusan menu terintegrasi) yang siap dianalisa, dimasukkan ke dalam *database*, atau dikonversi ke *format* Excel/CSV.

---

## 📦 Seperti Apa Bentuk Data yang Ditambang?

### A. Data Intelijen Restoran (Hasil Tahap 2)
Misalnya dari 60 restoran di Sukolilo, satu restoran memiliki wujud data seperti:
- `uid`: ID unik restoran dalam bentuk UUID (kunci utama sistem Gojek).
- `name`: Nama lengkap (*display name*) restoran.
- `full_url`: Tautan lengkap profil webnya.
- `latitude` & `longitude`: Titik koordinat GPS akurat.
- `rating_average`: Bintang/penilaian pelanggan.
- `price_level`: Level harga (skala 1 = murah, hingga 4 = sangat mahal).

### B. Data Katalog Menu (Hasil Tahap 3)
Di dalam setiap restoran (contoh: "A&W Mall Galaxy" memiliki 14 kategori dengan total 122 item), tiap menunya menyimpan data:
- `item_uid`: Kunci unik tiap produk makanan.
- `item_name`: Nama produk (contoh: "GIFTING A - 4 Aroma Chicken").
- `item_description`: Deskripsi detail (ukuran porsi, *topping* tersedia, dll.).
- `price_units`: Harga aktual dalam rupiah (contoh: `189500`).
- `image_url`: Tautan menuju foto makanan beresolusi tinggi di peladen (*server*) Gojek.
- `item_status`: Bendera angka 1 (makanan berstatus aktif/tersedia) atau angka lainnya untuk stok habis.

---

## 🛡️ Seni Menghindari Blokir (Strategi Hardening)
Sistem ini menggunakan teknik siluman untuk menghindari pemblokiran Cloudflare maupun sistem perlindungan GoFood otomatis:

1. **Daur Ulang Sesi (*Session Reuse*):** Sesi awal selalu disimpan (`storage_state.json`) dan dipakai setiap berkunjung. Skrip tidak melakukan permintaan baru dari nol yang bisa mencurigakan server.
2. **Karakteristik Pengunjung Alami (*Anti-detection Headers*):** Memalsukan parameter *User-Agent* agar sistem mengira (*request* berasal dari Chrome di Windows 10, menggunakan pengaturan bahasa `id-ID` dari zona waktu *Asia/Jakarta*.
3. **Pencicilan Beban (*Micro-Batching*):** Menumpuk tugas dibagi per kelompok. Default 5 restoran sekali jalan, untuk menghindari terjadinya peringatan lalu lintas terlalu padat (*Rate Limit*).
4. **Jeda Santai (*Polite Scraping*):** Menambahkan waktu henti acak (`random.uniform(3, 7)` detik) antar restoran meniru rata-rata kecepatan klik manusia.
5. **Bendera Mode Siluman (*Browser Flags*):** Menginjeksi argumen mutakhir `--disable-blink-features=AutomationControlled` guna menyabotase kode *tracker* GoFood agar tidak mendeteksi mode otomasi Playwright.

---

## 🏁 Kesimpulan Bukti Konsep (PoC) & Langkah Berikutnya
Pengujian eksperimental yang dilakukan di area Sukolilo mencatatkan **tingkat keberhasilan 100% (3/3 sukses)** pada percobaan Batch Menu yang mengangkut total **222 menu** tanpa mengalami kras atau blokir WAF satupun.

**Langkah Lanjutan:**
1. **Skala Penuh (*Scale Up*):** Jika sebelumnya hanya menguji 3 resto, sekarang jalankan ekstraktor menu untuk meraup 60 profil outlet di Sukolilo sepenuhnya.
2. **Ekspor Data:** Buat logika untuk menggabungkan (*join*) JSON restoran dan menu berdasarkan atribut `uid` menjadi format lajur kolom *CSV* yang dapat dimuat ke *dashboard* Data Studio atau dibaca analis.
3. **Ekspansi Area:** Karena sudah terbukti kebal blokir, pipeline ini siap diulang (direplikasi) untuk area yang lebih besar (Gubeng, Tegalsari, dll.).
