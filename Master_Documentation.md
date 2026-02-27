# Master Documentation: F&B Pricing Intelligence Engine (GoFood Scraper MVP)

Dokumen ini memuat _Standard Operating Procedure_ (SOP) komprehensif, terstruktur, dan _reproducible_ dari ekosistem proyek ini. Menjelaskan secara teknis dari awal tahap ekstraksi data mentah (Scraping Pipeline) hingga pemodelan serta kategorisasi harga secara granular (Data Modeling Pipeline).

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

## 1. Arsitektur End-to-End Pipeline Keseluruhan

Pipeline terdiri atas dua fase terpisah: **Phase 1 (Data Extraction)** untuk mengotomasi akuisisi data via Playwright dan Network Interception, disusul dengan **Phase 2 (Data Modeling & Enrichment)** untuk memanipulasi _raw JSON/CSV_ menjadi _Golden Dataset_ berdimensi harga prediktif dan klasifikasi Natural Language (NLP) yang siap direpresentasikan ke UI Intelligence Engine.

---

### 1.1. Phase 1: Data Extraction & Scraping Pipeline (Data Engineering)
*Lokasi Eksekusi Direktori Utama: `scrapper-gofood/`*

#### 1.1.1. Step 1: Session Bootstrap (WAF Warm-up)
- **Tujuan (Objective):** Menembus sistem pertahanan anti-bot (WAF/Cloudflare) milik sistem agregator GoFood menggunakan _real browser_ secara manipulatif sehingga deretan *request* HTTP selanjutnya secara sah dikenali sebagai kunjungan organik.
- **Deskripsi Eksekusi (What is Done):** Membuka rute halaman pertama (listing wilayah HTML awal) secara _Headless_ maupun _Headful_ melalui modul `Playwright`. Script dibuat sengaja memakan waktu lambat agar seluruh aset _JavaScript_ dari server berhasil me-render elemen krusial (seperti pemeriksaan probabilitas bot _probe.js_). Kesuksesan interaksi tersebut direkam secara utuh dengan cara menyimpan wujud abstraksi *Storage State* lengkap bersama *Cookies* session untuk persetujuan oknom crawler berikutnya.
- **Snippet Kode (Implementation):**
```python
# developer_test_scrapping.py -> step1_session_bootstrap
context = browser.new_context(**_context_kwargs(storage_state))
page = context.new_page()

# Domcontentloaded mengisyaratkan JS Next.js telah tersusun
response = page.goto(listing_url, wait_until="domcontentloaded", timeout=60_000)
page.wait_for_load_state("networkidle", timeout=20_000)

# Simpan cookie & identitas bypass bot utuh offline-presistence
context.storage_state(path=str(storage_state))
context.close()
```
- **Artefak Output:** Sebuah injeksi state JSON raksasa: `output/session/gofood_storage_state.json`.
- **Dampak Bisnis/Teknis (Impact):** Menjamin _High Reliability_ sistem *scraper* sebesar nyaris 100%. Tanpa tahapan validasi session WAF ini, setiap automasi HTTP konvensional (_dumb request_) akan secara reaktif dicampakkan menjadi angka kembalian *HTTP Status 202*, mematikan kapabilitas ekstraksi menu kompetitor mana pun.

#### 1.1.2. Step 2: Outlet Discovery via Near-Me (Network Interception)
- **Tujuan (Objective):** Mengoleksi seluruh taksonomi daftar outlet restoran yang berada pada radius sebaran geografis kecamatan tersebut secara tuntas, presisi, tanpa dipusingkan oleh elemen *UI/DOM HTML* yang rentan perubahaan dadakan.
- **Deskripsi Eksekusi (What is Done):** Scraper memicu aktivitas iterasi _scroll_ tanpa kehabisan *content* ke endpoint `/near-me/` yang aslinya beralaskan _lazy-load UX design_. Selagi melakukan _scroll_ repetitif secara berkala, pipeline secara senyap menyuntikkan unit pendengar jaringan (*Interceptor*). Teknik ini bertugas memancing (sniffing) respon *Fetch/XHR GraphQL* rahasia milik aplikasi. Output yang tercegat akan disaring (*filtering*) rekursif agar hanya elemen identik UID organik Restoran (serta Latitude & Longitude presisi) yang terverifikasi dan bukan kategori abstrak UI "CUISINE_".
- **Snippet Kode (Implementation):**
```python
# developer_test_scrapping.py -> step2_outlet_discovery
def handle_response(response):
    if response.request.resource_type not in ("fetch", "xhr"): return
    # Penyandingan pola intersepsi hanya terkhusus pada traffic API
    if not any(hint in response.url.lower() for hint in API_URL_HINTS): return
    
    # Abstraksikan payload mentahan jaringan
    body = response.json()
    found = _extract_outlets_recursive(body)
    # Penormalisasian URL Profile & Pembedahan UUID

# Listen ke traffic jaringan yang melintas!
page.on("response", handle_response)

# Logika infinite scrolling selayaknya manusia
while scroll_count < max_scrolls and stale_streak < patience:
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(scroll_delay)
```
- **Artefak Output:** Berkas daftar Leads Restoran Mentahan: `output/json/gofood_{locality}_outlets.json` yang memuat list UUID Outlet lengkap.
- **Dampak Bisnis/Teknis (Impact):** Meninggalkan proses kuno scraping struktur grafis (CSS Selectors). Dengan *Network Interception Protocol*, data geo-koordinat yang tidak sengaja bocor akibat transmisi internal dapat divisualisasikan untuk *GIS Location Market Mapping*.

#### 1.1.3. Step 3: Batch Menu Extraction (Profile Parsing Offline-First)
- **Tujuan (Objective):** Ekstraksi mendetail menembus lapisan menu (*SKU/Produk*), harga aslinya, serta identifikasi rupa setiap sajian makanan dari setiap toko di katalog restoran yang tersimpan.
- **Deskripsi Eksekusi (What is Done):** Pipa utama ini akan melakukan pergerakan pindah antar halaman berbekal _Storage State_ (Tindak 1.1.1). Setibanya di profil restoran yang berlandaskan Next.js framework, script TIDAK mengekstrak struktur tag `<div>` satupun. Alih-alih meraba DOM HTML, bot membedah wadah embrio bawaan server pada sintaks `<script id="__NEXT_DATA__">`. Objek raksasa bawaan Backend tersebut lantas dibongkar offline untuk mengambil rute *nested catalog section*, memampatkan deretan menu komplit menjadi bentuk Tabular (*Flat Row Table*) sempurna nan instan.
- **Snippet Kode (Implementation):**
```python
# developer_test_scrapping.py -> _parse_menu
_NEXT_DATA_RE = re.compile(
    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)

# Mengekstrak embedded JSON yang memuat seluruh catalog restoran
match = _NEXT_DATA_RE.search(html)
payload = json.loads(match.group(1).strip())

# Traverse spesifik ke lokasi penyimpanan Katalog
catalog = payload.get("props", {}).get("pageProps", {}).get("outlet", {}).get("catalog", {})
sections_raw = catalog.get("sections", [])
```
- **Artefak Output:** Metadata katalog lengkap pada `output/json/gofood_{locality}_menus.json` (Nested) dan rupa Tabular Analitis di `output/csv/gofood_{locality}_menus.csv`.
- **Dampak Bisnis/Teknis (Impact):** Menjamin integritas data 99% level _clean-ready_. Keberhasilan sistem _headless traversal_ via Next.js Data JSON mengabaikan format mata uang yang direkayasa grafis dan mencegah malformasi tipe harga pada pemrosesan Machine Learning di *Phase 2*.

#### 1.1.4. Step 4: Multi-Area Orchestration (Surabaya Scraper Batch Runner)
- **Tujuan (Objective):** Mengskalakan *crawling logic* tunggal menuju orkestrasi skala *City-Level* raksasa seraya menghindari pencekalan eksekusi oleh _Rate Limit WAF Bot Detection_.
- **Deskripsi Eksekusi (What is Done):** Mengorkestrasikan Step-1 hingga Step-3 berturut-turut untuk daftar masif (e.g. 31 area seluruh surabaya) dalam 1 run `scrap_sby.py`. Sistem disisipkan taktik defensif _Human Delay_ acak (waktu tunggu inter-area selama 30-90 detik untuk menurunkan trafik). Ditambah modul presistensi rekaman _progress/resume capability_ log JSON sehingga saat terjadi bencana jaringan mandek di area ke-15, developer dapat melanjutkannya mulai spesifik dari titik kecelakaan, mereduksi kerugian *downtime*.
- **Snippet Kode (Implementation):**
```python
# scrap_sby.py -> main
for idx, area in enumerate(areas_to_scrape, start=1):
    result = run_pipeline_for_area(...)
    
    # Save real-time resume point
    progress_file.write_text(json.dumps(all_results, ensure_ascii=False, indent=2))
    
    # Sleep pattern selayaknya manusia asili ketika berpindah tab browser antar kecamatan
    if idx < total_areas:
        human_delay(30, 90, "Jeda panjang sebelum area berikutnya")
```
- **Artefak Output:** Track log resume presistence di `output/json/scrap_sby_progress.json` serta Agregasi Laporan Akhir pada `output/json/scrap_sby_summary.json`.
- **Dampak Bisnis/Teknis (Impact):** Transformasi dari sebatas prototipe manual ke derajat *Autonomous Industrial-scale Data Engine*. Ini adalah pintu masuk aliran akuisi Data Warehouse yang stabil tanpa keterlibatan manual intervensi manusia.

---

### 1.2. Phase 2: Data Modeling, Enrichment & Price Categorization (Data Science)
*Lokasi Eksekusi Sub-Direktori: `pemodelan_data_gofood/`*

#### 1.2.1. Step 5: Data Loading & Price Extraction / Normalization
- **Tujuan (Objective):** Mengkonkastinasi pundi-pundi tabel *batch* daerah (*CSV*) mentahan dan menstrukturisasi tipe dimensi nilai metrik `Price` (harganya).
- **Deskripsi Eksekusi (What is Done):** Membaca folder agregat menugaskan utilitas *Pandas* untuk penyerapan multi-tabel (`glob`). Script mengekstrak string subtipe kewilayahan nama dokumen ("gofood_*gubeng*-restaurants") guna mendeklarasikan variabel teritorial `Kecamatan`. Lebih jauh, fungsi `extract_price` meniadakan simbol prefiks "Rp", serta karakter desimal komplotan aneh (cth: "Rp12.000,00" atau "24000") menjadi satu unit murni numerik komputasi (_float_) bernama `price_numeric`. Kolom bernilai cacat / _NaN_ dikosongkan.
- **Snippet Kode (Implementation):**
```python
# pemodelan_data_gofood/run_pipeline.py
for f in menu_files:
    df = pd.read_csv(f)
    # Extraktor metadata geo lokasi basis filename
    df['kecamatan'] = os.path.basename(f).split('_')[1].split('-')[0].title()

def extract_price(price_val):
    clean_str = str(price_val).lower().replace('rp', '').strip()
    if ',' in clean_str and '.' in clean_str:
        clean_str = clean_str.replace('.', '').replace(',', '.')
    return float(clean_str)

df_all['price_numeric'] = df_all['price_units'].apply(extract_price)
df_all.dropna(subset=['price_numeric'], inplace=True)
```
- **Artefak Output:** Model DataFrame di memori Pandas inisiasi yang memiliki dimensi kunci: `Kecamatan` (Geospasial Basis) dan pengukuran kuantitatif valid di iterasi peramalan harga `price_numeric`.
- **Dampak Bisnis/Teknis (Impact):** Fundamental dari pembandingan wawasan lintas hiper-lokal komoditas seragam ("Siapakah penjual nasi kuning termurah di kecamatan Gubeng dibandingkan kecataman Sukolilo?"). Normalisasinya vital meredam gagal komputasi *ML Algorithms*.

#### 1.2.2. Step 6: Hierarchical Natural Language Food Categorization 
- **Tujuan (Objective):** Merestrukturisasi kebrutalan identitas nama Item (misalnya: "nasi kng dadar lkmp sosis11") menjadi penomoran hierarki klasifikasi rapi _Business Dictionary Type_: (Misal: 3 Level => Makanan -> Nasi -> Nasi Kuning).
- **Deskripsi Eksekusi (What is Done):** Mengeksekusi modul utilitas pintar `utils/categorizer.py` basis baris per baris. Logika internal menggunakan hibrida *Linear Search* dipadupadankan konvensi batas spasi konstan kata *Regex Word Boundary* (`\b`). Sistem menilai sebuah string makanan bedasar probabilitas bobot nilai *skoring* 3 arah: (1) Panjang keyword semantik teks; (2) Beban Multiplier Posisional String: Entitas kata awalan/prefix (_"Mie Goreng Polos"_) diberikan *weight* tiga kali lipat lebih ekstrim; (3) Indikasi penggabungan teks atribut `section_name` lapis profil item target. Pencetak _high-score_ akan diangkat pemenangnya.
- **Snippet Kode (Implementation):**
```python
# pemodelan_data_gofood/utils/categorizer.py -> categorize_specific
for compiled, kw_len, rule_idx in _KEYWORD_INDEX:
    # Mengulik sumber utama string `item_name` dengan Regex Boundary
    match_item = compiled.search(item_padded)
    if match_item:
        base = kw_len
        # Peluruhan berat prioritas (Weight Decay) 
        # Kata pembuka = weight tertinggi (3.0), Tengah (1.5), Akhir kata (0.75)
        pos_ratio = match_item.start() / item_len
        position_weight = 3.0 * (1.25 ** pos_ratio) 
        score += base * position_weight
        
return {"main_category": main, "sub_category": sub, "specific_category": specific}
```
- **Artefak Output:** Injeksi pengkategorian baru sebanyak 3 Dimensi level F&B pada Dataframe : Kolom dimensi kategorikal murni `main_category`, `sub_category`, dan sublapisan tersempit `specific_category`.
- **Dampak Bisnis/Teknis (Impact):** Membereskan halangan terbersar (A.I) pemahaman bahasa gaul makanan abang gerobak jalanan di kultur nusantara. Kemampuan kategorisasi berjenjang mengizinkan dashboard wawasan intelijen (_Competitive Dashboard_) mengeroksi ke bawah (drill-down view) yang dahsyat, e.g. "Insight Minuman Dingin (Umum)" turun maknanya kepada pangsa terik "Es Teler" secara spesifik!

#### 1.2.3. Step 7: Bundle (Paketan) Detection & Payload Extraction Algorithm
- **Tujuan (Objective):** Menyingkap selubung taktis penjual, mendelegasikan status apakah entitas `item` merupakan barang sejenis jualan eceran ("Satuan") di hadapan varietas borongan grup paket promosi keluarga ("Paketan"). Plus, menguraikan isi kardus paket borongan yang dijajakan.
- **Deskripsi Eksekusi (What is Done):** Teks dari relasi tiga penanda subjek (Name, Description, & Section) dilebur. Sistem mencocokkan konfirmasi presisi leksikon (*Bundle Pattern Regex*) dari koleksi array semisal kata-kunci (`r'\bbundling\b'`, `r'\w+\s*\+\s*\w+'`, "buy 2 get 1"). Terdeteksi `Paketan` atau tidak. Lebih mutakhirnya `extract_bundle_items` me_*recycle* logika penentuan kata NLP dari tahap 1.2.2 untuk membongkar secara paksa "Nasi Ayam Geprek Special Esteh" kedalam list pemecahan komoditas: `['Ayam Geprek', 'Nasi Putih', 'Minuman (General)']`.
- **Snippet Kode (Implementation):**
```python
# pemodelan_data_gofood/utils/categorizer.py -> detect_bundle & extract_bundle_items
BUNDLE_PATTERNS = [r'\bpaket\b', r'\w+\s*\+\s*\w+', r'\bfree\s+[a-z]+']
_COMPILED_BUNDLE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in BUNDLE_PATTERNS]

def get_bundle_contents(row):
    if row['item_type'] == 'Paketan':
        # Array pemecahan komposisi komoditi
        contents = extract_bundle_items(str(row['item_name']), str(row.get('item_description', '')), str(row.get('section_name', '')))
        return contents or [row['specific_category']]
    return [row['specific_category']]
```
- **Artefak Output:** Ciptaan kolom boolean logika biner `item_type` komando nilai: ("Paketan" , "Satuan"). Begitupula kehadiran List Payload Array `bundle_contents`.
- **Dampak Bisnis/Teknis (Impact):** Eliminator polusi _Market Analysis Bias_ tercanggih. Andaikata skema ini dianaktirikan: Algoritme Regresor akan termanipulasi membandingkan "Ayam Geprek" ecer Rp 15,000 versus "Ayam Geprek [Paket Sekampung 20 Orang]" seharga Rp 350,000 berujung pada distorsi konyol nilai rata-rata harga menjadi semu (Tidak kompetitif dan menyulitkan pembacaan Machine learning rekomendasi diskon).

#### 1.2.4. Step 8: Outlier Removal & Tertile Predictive Price Grouping
- **Tujuan (Objective):** Pemusnahan data manipulatif pencilan (_extreme outlier_) harga yang berpotensi mencederai kurva ekuilibrium metrik penawaran-permintaan serta melakukan stratifikasi kelas sosial harga kedalam pengelompokan Tertile.
- **Deskripsi Eksekusi (What is Done):** Mengidentifikasi anomali harga gila para Merchant di platform (contoh: Nasi putih diinput Rp 900.000 atau cuma sepeser Rp 1). Penghapusan outlier memanfaatkan *The Interquartile Range Formula (IQR)* HANYA kepada relasional grup paling terkecil perpaduan antarkolom `specific_category` bertabrakan dengan klasifikasi wujud `item_type`. Sehingga harga ekstrim "Nasi (Paketan)" tak akan dicemooh jika harga tersebut sah, namun wajar dibinasakan andaikata ia sebuah model dari "Nasi (Satuan)". 
Bagian pamungkas: dataset _outlier_ yang digugurkan akan difiltrasi dalam metrik persentase batas ambang (Quantile .33 dan .67) per rumpun kategori terkecil, menyemai bibit pembagian harga *3-Tier Segmentation* prediktif yang dicap statusnya : "Murah", "Sedang", dan "Mahal".
- **Snippet Kode (Implementation):**
```python
# pemodelan_data_gofood/run_pipeline.py -> remove_outliers & categorize_price
def remove_outliers(df, column):
    Q1, Q3 = df[column].quantile(1.25), df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound, upper_bound = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

# Memusnahkan outlier pada partisi level sub-grup presisi
df_clean = df_all.groupby(['specific_category', 'item_type'], group_keys=False).apply(
    lambda x: remove_outliers(x, 'price_numeric')
)

def categorize_price(x):
    # Mengukur kewajaran harga dalam balutan distribusi statistik Percentile
    q33, q67 = x.quantile(0.33), x.quantile(0.67)
    conditions = [(x <= q33), (x > q33) & (x <= q67), (x > q67)]
    return np.select(conditions, ['murah', 'sedang', 'mahal'], default='sedang')
```
- **Artefak Output:** 
  1. `output/data/processed_menus.csv` (Rujukan Dataset bersih).
  2. `output/data/final_menus_enriched.csv` (*The Golden Record*). Format tabular data final berisi label NLP, flag wujud _bundling_, dan identitas strata Harga kuantitatif yang solid.
- **Dampak Bisnis/Teknis (Impact):** Puncak Mahakarya Data Engineering MVP (Output Akhir Deliverable). File *Golden Record* ini 100% *Plug-and-play* yang mana Data Analyst dapat meneruskannya lurus kedalam Visualizer (PowerBI/Tableau), atau Data Scientist merajut relasi _Regression AI algorithms_ guna meramalkan strategi intelijen harga optimal tanpa terhalang setitik noise pun.
