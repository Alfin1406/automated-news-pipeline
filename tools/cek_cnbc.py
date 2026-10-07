import requests
from bs4 import BeautifulSoup

print("Melakukan Diagnosis Server CNBC...")
url = "https://www.cnbcindonesia.com/tech/indeks/7/1"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}

res = requests.get(url, headers=headers)
print(f"Status Respon Server: {res.status_code}")

if res.status_code == 200:
    print("✅ Berhasil masuk ke web! Tidak diblokir.")
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Mencari tahu tag apa yang sebenarnya dipakai CNBC untuk membungkus berita
    artikel = soup.find_all('article')
    list_li = soup.find_all('li')
    
    print(f"Jumlah tag <article> ditemukan: {len(artikel)}")
    print(f"Jumlah tag <li> ditemukan: {len(list_li)}")
    
    if len(list_li) > 0:
        print("\nContoh isi teks dari salah satu tag <li>:")
        # Mengambil sampel teks dari elemen list ke-5 (biasanya berita mulai dari sini)
        print(list_li[5].text.strip()[:150])
else:
    print("❌ Kita diblokir oleh sistem anti-bot CNBC (Forbidden).")