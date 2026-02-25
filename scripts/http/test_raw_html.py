import requests
from pathlib import Path


def test_gofood_html():
    # 1. Tentukan target URL (Ganti kecamatan jika perlu)
    target_url = "https://gofood.co.id/surabaya/sukolilo-restaurants"

    # 2. Gunakan User-Agent standar agar tidak langsung diblokir
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        print(f"[EXECUTING] Menembak URL: {target_url}...")

        # Lakukan HTTP GET Request
        response = requests.get(target_url, headers=headers, timeout=10)

        # Cetak Status Code untuk melihat reaksi server
        print(f"[RESULT] Status Code: {response.status_code}")

        if response.status_code == 200:
            print("[SUCCESS] Berhasil masuk! Menyimpan output...")
        elif response.status_code == 403:
            print("[WARNING] Akses Ditolak (403 Forbidden). Terkena blokir Anti-Bot/WAF.")
        else:
            print(f"[WARNING] Mendapat respons aneh: {response.status_code}")

        # 3. Simpan seluruh respons mentah ke dalam file HTML
        output_path = Path("output/html/gofood_raw_output.html")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(response.text, encoding="utf-8")

        print(f"[DONE] File berhasil disimpan sebagai '{output_path}'.")
        print("Silakan buka file tersebut di Code Editor atau Browser untuk dianalisis.")

    except Exception as e:
        print(f"[ERROR] Uji coba gagal: {e}")


if __name__ == "__main__":
    test_gofood_html()
