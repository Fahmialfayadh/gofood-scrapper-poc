# Dokumentasi Lengkap: Pipeline Scraping Data GoFood

Dokumentasi ini menjelaskan **apa**, **mengapa**, dan **bagaimana** sistem *scraper* GoFood pada proyek ini dirancang dan bekerja secara *step-by-step*, sejalan dengan panduan alur file yang ada.

---

## 0. Pendahuluan: Untuk Apa Aplikasi Ini Dibuat?

### 0.1 Deskripsi Produk & Goals

Deskripsi produk: **F&B Market Intelligence Platform**

Aplikasi ini adalah platform intelijen harga dan database harga menu berbasis geospasial yang memberdayakan UMKM Kuliner untuk mengambil keputusan bisnis berbasis data (*data-driven*).

Aplikasi ini menyediakan data outlet/restoran GoFood beserta menu dan harga yang ada di dalamnya. Data ini sangat berguna untuk keperluan analisis pasar, riset kompetitor, dan pengambilan keputusan bisnis bagi para pelaku usaha di bidang makanan dan minuman (F&B).

### 0.2 Masalah yang Diselesaikan (The Pain Point)

Saat ini, UMKM F&B sering kali menetapkan harga jual dan membuat menu hanya bermodalkan "tebak-tebakan" atau feeling. Mereka buta terhadap peta persaingan lokal. Untuk mengetahui harga pasaran "Ayam Penyet" atau "Kopi Susu" di radius 2 kilometer dari warung mereka, pemilik UMKM harus membuka aplikasi GoFood/GrabFood secara manual, mencatat satu per satu, yang mana itu sangat melelahkan, tidak efisien, dan datanya tidak bisa dianalisis secara statistik.

### 0.3 Solusi yang Ditawarkan (The Solution)

Kami menghadirkan platform **market intelligence interaktif berbasis geospasial**.

Pengguna (UMKM) cukup menentukan titik lokasi usaha mereka di atas peta. Secara instan, sistem akan memproses koordinat tersebut dan menyajikan **dashboard analitik komprehensif** yang memetakan anatomi persaingan lokal secara utuh — mulai dari:

- Sebaran kompetitor terdekat
- Ragam menu yang ditawarkan pasar
- Kalkulasi rata-rata harga secara real-time

Pendekatan ini memungkinkan UMKM memahami struktur pasar mikro (hyperlocal market) secara presisi dan berbasis data.

### 0.4 Fitur Utama (Core Features)

#### 0.4.1 Head-to-Head Price Comparison

Platform membedah dan membandingkan struktur harga dari ratusan menu di sekitar pengguna.

Melalui visualisasi data yang intuitif, dashboard menyajikan insight langsung.
Contoh:

> 60% kompetitor di area Sukolilo mematok harga Nasi Goreng di kisaran Rp15.000 – Rp20.000.

Fitur ini membantu pelaku usaha menentukan positioning harga secara rasional dan kompetitif.

#### 0.4.2 AI-Powered Menu Categorization

Menggunakan teknologi **Natural Language Processing (NLP)** untuk:

- Menormalisasi data menu yang tidak terstruktur
- Mengelompokkan ribuan variasi nama menu
- Mengubah data mentah menjadi kategori standar siap analisis

Contoh kategori:

- Olahan Ayam
- Olahan Mie
- Aneka Minuman

Hasilnya adalah perbandingan yang benar-benar _apple-to-apple_.

#### 0.4.3 Margin Optimizer (Price Disparity Insight)

Mesin analitik menghitung selisih harga antara pasar online dan offline.

Fitur ini menghasilkan:

- Rekomendasi persentase mark-up optimal
- Simulasi margin setelah potongan platform delivery
- Strategi harga agar tetap kompetitif tanpa menggerus profit

UMKM dapat menyesuaikan harga secara presisi, bukan berdasarkan intuisi semata.

### 0.5 Keunggulan Teknologi (The Secret Sauce)

Keunggulan utama platform terletak pada arsitektur pengolahan data geospasial presisi tinggi yang ditenagai oleh **PostGIS**, dipadukan dengan pipeline agregasi data berskala besar.

Alih-alih mengandalkan survei manual yang lambat dan bias, sistem secara dinamis:

- Memetakan ribuan titik data pasar
- Menyinkronkan informasi harga dan menu
- Menstrukturkan data menjadi insight visual siap pakai

Pendekatan ini memastikan keputusan bisnis UMKM selalu berbasis data intelijen yang akurat dan up-to-date.

### 0.6 Visi Bisnis & Skalabilitas (The Commercial Roadmap)

Sebagai **Minimum Viable Product (MVP)**, platform ini memvalidasi nilai melalui pengolahan data publik.

Tahap berikutnya adalah ekspansi menuju model **B2B Data Partnership Ecosystem**, dengan positioning sebagai jembatan strategis antara:

- Jutaan UMKM yang membutuhkan market insight lokal
- Agregator besar (seperti Gojek dan Grab) melalui jalur API Enterprise resmi

Strategi ini membuka peluang monetisasi data yang saling menguntungkan dan membangun ekosistem intelijen pasar berbasis kolaborasi.

### 0.7 Outcome, Target Pengguna, dan Tujuan Proyek

**Outcome:**  
Platform ini bukan sekadar alat analitik, tetapi fondasi ekosistem intelijen pasar UMKM berbasis geospasial yang skalabel, presisi, dan siap diintegrasikan secara komersial.

- **Target pengguna:** para pengusaha F&B yang membutuhkan data restoran dan menu sekitar lokasi yang ditentukan untuk melakukan analisis pasar, harga, dan membantu *decision making* untuk usahanya.
- **Tujuan utama:** melakukan ekstraksi data restoran dan menu dari sistem GoFood dengan cara yang efisien, akurat, dan tahan terhadap mekanisme keamanan anti-bot yang diterapkan oleh GoFood.
- **Data yang didapat:** dilakukan analisis lebih lanjut seperti **mengkategorikan jenis harga (mahal, sedang, murah), mengkategorikan nama menu (contoh: ayam goreng, bebek goreng, burger), algoritma pencarian yang kompeten** untuk membantu pengguna dalam memahami pasar, memantau kompetitor, dan membuat keputusan bisnis yang lebih baik.

Dengan data yang diperoleh, pengguna dapat melakukan analisis pasar, riset kompetitor, dan pengambilan keputusan bisnis yang lebih baik.

---

## 1. Fase 1 (Scraping data restoran): Tantangan dan Solusi

Tentunya, sebelum membangun aplikasi database restoran dan menu, kita harus bisa mendapatkan data mentahnya terlebih dahulu.

### 1.1 Target sumber data utama: **GoFood**

Namun, GoFood memiliki sistem keamanan yang cukup ketat untuk mencegah akses ilegal atau scraping data secara massal.

**Masalah:** Apabila kita mencoba mengambil data menggunakan metode biasa (sebuah *dumb bot* yang memakai skrip dasar seperti `curl` atau modul `requests`), server GoFood akan segera mendeteksinya sebagai akses ilegal, lalu memblokir koneksi kita (status `202` atau *challenge page* seperti `probe.js`).

**Solusi Eksklusif:** Sistem ini dibangun menggunakan **Playwright**, yakni sebuah utilitas otomasi *browser* (peramban). Dengan Playwright, skrip kita "meminjam" mesin peramban sungguhan (Chromium) untuk berperilaku, menunggu, dan mengeksekusi *JavaScript* persis selayaknya pengguna manusia asli, sehingga sistem keamanan dapat dilewati.

### 1.2 Prinsip Desain Scraper: Alasan di Balik Sistem

Sistem ini tidak dirancang secara sembarangan, melainkan didasari oleh tiga prinsip arsitektur pokok:

1. **Memanfaatkan JSON/API Tersembunyi (Bukan *DOM Parsing*)**
   - **Kelemahan *DOM Parsing*:** Mengandalkan tag HTML (seperti `<div class="harga">`) sangat rapuh. Jika GoFood mengubah sepotong kecil desain *interface*-nya (UI), *scraper* akan langsung rusak (error).
   - **Solusi Kuat:** Situs GoFood (yang dibangun menggunakan kerangka Next.js) menyimpan seluruh datanya secara rapi dalam format JSON tersembunyi, baik lewat `<script id="__NEXT_DATA__">` maupun trafik komunikasi API internal (*XHR/fetch*). Menambang dari lapisan data mentah ini jauh lebih akurat dan antirusak.
2. **Offline-First Analysis**  
   Setelah HTML/JSON awal ditarik, analisa data dilakukan secara *offline* untuk mempercepat pengerjaan dan menjaga beban lalu lintas jaringan (*network payload*) tetap ringan.
3. **Penyimpanan Sesi Secara Berantai**  
   Setiap melewati pengecekan (*antibot*), "identitas lolos" atau sesi *cookies* wajib disimpan dan didaur ulang untuk permintaan (*request*) ke halaman berikutnya.

---

### 1.3 Alur Kerja File: Step-by-Step Pipeline

Alur pengeksekusian dibagi menjadi 3 Tahap berurutan. Setiap skrip mewakili satu langkah logis, dirancang saling melengkapi dan tak terpisahkan.

#### 1.3.1 Tahap 1: Mengantongi "Tiket Masuk" (Session Bootstrap)

**Tujuan:** Mendapatkan validasi dari GoFood bahwa kita adalah "pengunjung sah", lalu merekam "sidik jari" sesinya.

- **Lokasi Skrip:** `scripts/playwright/test_playwright_gofood.py`
- **Cara Kerja:**  
  Skrip membuka browser (Chromium) secara otomatis dan membiarkan halaman utama GoFood (contoh: halaman wilayah) dimuat sepenuhnya. Dengan menunggu selesainya eksekusi Javascript, tantangan keamanan (*challenge*) berhasil disingkirkan.
- **Alasan di balik ini:** Dengan memancing dan "memanaskan" (*warm-up*) keamanan menggunakan *browser* asli di awal, kita meminimalkan risiko diblokir pada kunjungan ke ribuan restoran berikutnya.
- **Output:** Identitas disimpan ke `output/session/gofood_storage_state.json`.

#### 1.3.2 Tahap 2: Menyidap Daftar Restoran (Near-Me Outlet Discovery)

**Tujuan:** Mengumpulkan data berisi ratusan restoran target beserta rincian vitalnya (ID, koordinat, *rating*, dsb) secara senyap.

- **Lokasi Skrip:** `scripts/playwright/test_nearme_interceptor.py`
- **Cara Kerja:**  
  Skrip membuka tautan tipe wilayah *near-me* (seperti `/near-me/`). Halaman GoFood me-muat lebih banyak restoran ketika pengguna menyapukan layar dari atas-ke-bawah (*infinite scroll*). Skrip meniru gerakan rentetan *scroll* ini, sambil menyadap (melakukan *network intercept*) semua respon API di saluran latar belakang, mengekstrak restoran sesungguhnya dan menyaring (*filtering*) kumpulan iklan / data palsu yang tidak relevan.
- **Alasan di balik ini:** Mencari manual atau mencari tautan di halaman depan sangat tidak efisien. Membiarkan sistem "berselancar tanpa disadari" lebih stabil dibandingkan mencoba menerka ID setiap restoran.
- **Output:** Menghasilkan senarai daftar yang matang ke file `output/json/gofood_nearme_outlets.json`.

#### 1.3.3 Tahap 3: Panen Massal Katalog Menu (Batch Menu Extraction)

**Tujuan:** Masuk menjebol jauh ke dalam halaman profil tiap restoran dan mengambil semua data produk menu dengan harga aslinya.

- **Lokasi Skrip:** `scripts/batch/batch_menu_scraper.py`
- **Cara Kerja:**  
  Skrip ini memakai hasil daftar restoran dari Tahap 2. Identitas "tiket sah" pada Tahap 1 ikut dibaca. Selanjutnya, sistem merayap mendatangi URL profil masing-masing restoran satu per satu. Dengan presisi, data muatan terstruktur (skema lengkap menu di dalam tag khusus `__NEXT_DATA__`) langsung disambar, dikategorisasikan (seksi promo, makanan ringan, minuman ritel), serta diekstrak komplit dengan harganya.
- **Alasan di balik ini:** Pola iterasi yang dilakukan satu demi satu menjaga kewarasan skrip (agar tidak gampang jebol karena memori habis) dan memungkinkan proses dapat dijeda/dilanjutkan kapan pun seandainya koneksi terputus tiba-tiba (*resumable micro-batching*).
- **Output:** Menyajikan laporan ke sepasang kembar `output/json/gofood_menus_master.json` dan wujud siap Excel `output/csv/gofood_menus_master.csv`.

---

### 1.4 Cara Pengoperasian Praktis

Jika tidak ingin repot mengeksekusi Tahap 1, 2, 3 secara manual, sistem ini menyediakan gerbang otomatis (Runner):

#### 1.4.1 Unified E2E Pipeline (Satu Wilayah)

Digunakan apabila menargetkan suatu kecamatan tanpa henti (tahap 1 hingga tahap 3 secara otomatis):

```bash
.venv/bin/python developer_test_scrapping.py --area surabaya --locality sukolilo-restaurants --limit 5
```

Perintah ini akan menyapu daftar hingga menemukan restoran dan mengeruk 5 menu utamanya ke dalam format file yang terpersonalisasi nama kecamatannya (seperti `gofood_sukolilo-restaurants_menus.json`).

#### 1.4.2 Multi-Area Runner (Ekspansi Skala Kota)

Digunakan manakala operasi yang masif dilakukan dalam beberapa teritori lintas kecamatan (contoh untuk Surabaya multi-area):

```bash
.venv/bin/python scrap_sby.py --limit 20
```

Sistem akan menjalankannya berturut-turut pada 6 kecamatan, melaporkan rekap progres, mendata restoran tanpa menu atau tertimpa error, serta tidak tergesa-gesa.

---

### 1.5 Strategi "Siluman" Penolak Blokir (Hardening)

Apa yang membuat sistem ini begitu tangguh? Ada 5 protokol keamanan *anti-bot detection* di baliknya:

1. **Daur Ulang Sesi (*Session Reuse*):** Tidak mengetuk berulang kali tanpa status. Sesi (cookie & storage) diterbitkan ulang terus.
2. **Kamuflase (*Header Spoofing*):** Menyamar penuh menjadi Chrome pada Waktu Indonesia Barat (`Asia/Jakarta`) dan parameter bahasa identitas lokal (`id-ID`).
3. **Pencicilan Beban (*Micro-Batching*):** Memakai kombinasi limit / offset sehingga *traffic* tidak terlihat menyerang sekaligus dalam 1 milisekon.
4. **Jeda Manusiawi (*Polite Scraping*):** Rentang acak *(random delay)* 3 sampai 7 detik sebelum melompat ke restoran berikutnya meniru keraguan kursor manusia biasa.
5. **Sabotase Kode Pelacak (*Browser Flags*):** Skrip *browser* disuntikkan baris anti-otomatisasi `--disable-blink-features=AutomationControlled` guna memalsukan sensor Google yang lazim mendeteksi pergerakan non-manusia.

---

### 1.6 Anatomi Data Terekstrak

Eksekusi yang berhasil akan melahirkan laporan analitik ganda:

- **Dokumen JSON (Struktur Bersarang/Nested)**  
  Menyuguhkan pola hierarki mulai dari Restoran (Parent) ➔ Seksi Menu (Group) ➔ Item Detail. Struktur ini ideal digunakan bilamana sistem menancapkan ke wadah penyimpanan MongoDB atau aplikasi *backend*.
- **Tabel CSV (Bentuk Permukaan Tembus/Flat)**  
  Dokumen format tabulat pipih (tabel kolom-baris). Di setiap satu baris, identitas hidangan, harga satuan, dan porsi dipadatkan beserta label tempat restorannya bernaung. Format yang sangat bersahabat bagi keperluan agregasi data memakai aplikasi semacam Excel, Microsoft PowerBI, atau pustaka Pandas untuk kepentingan kecerdasan bisnis *(Business Intelligence)* serta observasi sentimen harga (*pricing intelligence*).
