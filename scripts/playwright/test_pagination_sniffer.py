import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

# Tempat menyimpan semua data API yang berhasil ditangkap
intercepted_data = []


TARGET_URL = "https://gofood.co.id/surabaya/sukolilo-restaurants"
OUTPUT_FILE = Path("output/json/gofood_pagination_sniff.json")
STORAGE_STATE = Path("output/session/gofood_storage_state.json")


def handle_response(response):
    # Kita hanya peduli dengan request berjenis fetch/xhr (API call)
    if response.request.resource_type in ["fetch", "xhr"]:
        url = response.url
        
        # Filter URL yang kemungkinan besar adalah API untuk memuat restoran
        # Keyword ini tebakan logis: graphql, search, restaurantsespon, explore, atau api
        if "graphql" in url or "api" in url or "search" in url:
            try:
                # Coba parse response-nya sebagai JSON
                json_response = response.json()
                
                # Simpan URL, Request Payload (jika ada), dan Response-nya
                data_packet = {
                    "url": url,
                    "method": response.request.method,
                    "post_data": response.request.post_data, # Ini penting untuk melihat payload cursor/page
                    "response": json_response
                }
                intercepted_data.append(data_packet)
                print(f"[SNIFFED] Berhasil menangkap data dari: {url}")
            except:
                pass # Abaikan jika bukan JSON (misal image atau text biasa)

def sniff_pagination():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        print("[PROCESS] Membuka browser dengan session state...")
        browser = p.chromium.launch(headless=False) # Kita set False dulu agar kamu bisa melihat scroll-nya
        if STORAGE_STATE.exists():
            context = browser.new_context(storage_state=str(STORAGE_STATE))
        else:
            print(f"[WARNING] Storage state tidak ditemukan: {STORAGE_STATE}. Session baru dipakai.")
            context = browser.new_context()
        page = context.new_page()

        # Pasang alat penyadap ke event 'response'
        page.on("response", handle_response)

        print(f"[PROCESS] Mengakses: {TARGET_URL}")
        page.goto(TARGET_URL, wait_until="networkidle")
        
        # Simulasi scroll ke bawah untuk memicu API Pagination
        print("[PROCESS] Memulai simulasi scroll (Infinite Scroll trigger)...")
        for i in range(3): # Kita coba 3 kali scroll paksa
            # Scroll ke paling bawah halaman
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            print(f"  -> Scroll ke-{i+1} dieksekusi, menunggu API merespons...")
            time.sleep(3) # Beri waktu agar request API selesai dan ditangkap oleh handler

        # Tutup browser
        browser.close()

        # Simpan hasil sadapan ke file JSON
        if intercepted_data:
            OUTPUT_FILE.write_text(
                json.dumps(intercepted_data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"\n[SUCCESS] Menangkap {len(intercepted_data)} payload API potensial!")
            print(f"Silakan buka '{OUTPUT_FILE}' untuk mencari data sisa restoran.")
        else:
            print("\n[FAILED] Tidak ada API pagination yang tertangkap. Perlu inspeksi manual selector/URL.")

if __name__ == "__main__":
    sniff_pagination()
