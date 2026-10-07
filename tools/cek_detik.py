import requests
from bs4 import BeautifulSoup

print("Diagnosis Struktur Web Detik Inet...")
url = "https://inet.detik.com/indeks?page=1"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}

res = requests.get(url, headers=headers)
soup = BeautifulSoup(res.text, 'html.parser')

print(f"Status Respon Server: {res.status_code}")
print(f"Jumlah tag <article>: {len(soup.find_all('article'))}")
print(f"Jumlah tag <div class='media'>: {len(soup.find_all('div', class_='media'))}")
print(f"Jumlah tag <div class='list-content__item'>: {len(soup.find_all('div', class_='list-content__item'))}")
print(f"Jumlah tag <h3> (biasanya judul): {len(soup.find_all('h3'))}")
print(f"Jumlah tag <h2> (biasanya judul): {len(soup.find_all('h2'))}")