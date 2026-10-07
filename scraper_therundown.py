import requests
from bs4 import BeautifulSoup
import json
import time
import random
import re
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine, inspect

# --- KONEKSI POSTGRESQL UNTUK CEK DATA ---
DATABASE_URL = "postgresql+psycopg2://postgres:alfin1406@host.docker.internal:5432/pln_intelligence_db"
engine = create_engine(DATABASE_URL)

def bersihkan_teks(teks):
    teks = re.sub(r'(?i)read more', '', teks)
    teks = re.sub(r'(?i)subscribe', '', teks)
    teks = re.sub(r'(?i)share this', '', teks)
    teks = re.sub(r'\s+', ' ', teks).strip()
    return teks

def standarisasi_tanggal_en(tgl_str):
    kamus_bulan = {
        'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
        'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
        'aug': 8, 'august': 8, 'sep': 9, 'september': 9, 'oct': 10, 'october': 10,
        'nov': 11, 'november': 11, 'dec': 12, 'december': 12
    }
    if not tgl_str:
        return datetime.now(), datetime.now().strftime("%Y-%m-%d")
    tgl_str = str(tgl_str).lower().strip()
    
    pola_teks = re.search(r'([a-z]+)\s+(\d{1,2}),?\s+(\d{4})|(\d{1,2})\s+([a-z]+)\s+(\d{4})', tgl_str)
    if pola_teks:
        if pola_teks.group(1):
            kata_bulan, hari, tahun = pola_teks.group(1), int(pola_teks.group(2)), int(pola_teks.group(3))
        else:
            hari, kata_bulan, tahun = int(pola_teks.group(4)), pola_teks.group(5), int(pola_teks.group(6))
        angka_bulan = kamus_bulan.get(kata_bulan) or kamus_bulan.get(kata_bulan[:3], 1)
        try:
            obj_waktu = datetime(tahun, angka_bulan, hari)
            return obj_waktu, obj_waktu.strftime("%Y-%m-%d")
        except ValueError:
            pass

    pola_iso = re.search(r'(\d{4})-(\d{2})-(\d{2})', tgl_str)
    if pola_iso:
        try:
            obj_waktu = datetime(int(pola_iso.group(1)), int(pola_iso.group(2)), int(pola_iso.group(3)))
            return obj_waktu, obj_waktu.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return datetime.now(), datetime.now().strftime("%Y-%m-%d")

def ekstrak_detail_rundown(url, headers):
    hasil = {"isi_berita": "Gagal mengekstrak isi teks.", "gambar": "https://via.placeholder.com/600x400?text=The+Rundown+AI", "tanggal_akurat": None}
    if not url.startswith('http'):
        url = 'https://www.therundown.ai' + url
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        div_isi = soup.find('article') or soup.find('div', class_=re.compile(r'(content|prose|body)'))
        if div_isi:
            paragraf = div_isi.find_all(['p', 'li'])
            if paragraf:
                teks_kotor = " ".join([p.text.strip() for p in paragraf if p.text])
                hasil["isi_berita"] = bersihkan_teks(teks_kotor)
                
        elemen_gambar = soup.find('meta', property='og:image')
        if elemen_gambar and elemen_gambar.get('content'):
            hasil["gambar"] = elemen_gambar.get('content')
            
        meta_date = soup.find('meta', property='article:published_time') or soup.find('meta', attrs={'name': 'publishdate'})
        if meta_date and meta_date.get('content'):
            _, tgl_benar = standarisasi_tanggal_en(meta_date.get('content'))
            hasil["tanggal_akurat"] = tgl_benar
        else:
            tgl_elemen = soup.find('time') or soup.find('span', string=re.compile(r'202\d'))
            if tgl_elemen:
                _, tgl_benar = standarisasi_tanggal_en(tgl_elemen.text)
                hasil["tanggal_akurat"] = tgl_benar
    except Exception:
        pass
    return hasil

def main():
    TARGET_BULAN_MUNDUR = 5
    batas_waktu_kadaluarsa = datetime.now() - timedelta(days=TARGET_BULAN_MUNDUR * 30)

    print(f"🚀 Membangun Pipeline: Scraper 3 (The Rundown AI - Global)")
    print(f"Batas Kadaluarsa: {batas_waktu_kadaluarsa.strftime('%Y-%m-%d')}")
    print("=" * 70)

    # 1. CEK LINK YANG SUDAH ADA DI DATABASE
    existing_links = set()
    inspector = inspect(engine)
    if inspector.has_table('tabel_berita_ai'):
        try:
            df_existing = pd.read_sql("SELECT link FROM tabel_berita_ai WHERE sumber='The Rundown AI'", con=engine)
            existing_links = set(df_existing['link'].tolist())
            print(f"✅ Ditemukan {len(existing_links)} artikel The Rundown AI lama di Database.")
        except Exception:
            pass

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    semua_berita = []
    halaman = 1
    pencarian_selesai = False

    print("TAHAP 1: Menjelajahi halaman (Auto-Stop jika data sudah ada)...")
    while not pencarian_selesai:
        # Mengubah format URL paginasi menjadi parameter kueri (?page=)
        url = "https://www.therundown.ai/articles-category/ai" if halaman == 1 else f"https://www.therundown.ai/articles-category/ai?page={halaman}"
        print(f" -> Memeriksa halaman {halaman}...", end='\r')
        
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code != 200:
                print(f"\n[!] Server menolak akses di halaman {halaman} (Status Code: {res.status_code})")
                break
                
            soup = BeautifulSoup(res.text, 'html.parser')
            kartu_artikel = soup.find_all('a', href=True)
            
            if not kartu_artikel:
                print(f"\n[!] Tidak ada elemen artikel (kartu_artikel kosong) di halaman {halaman}.")
                break
                
            artikel_ditemukan_di_halaman_ini = False
            jumlah_artikel_sudah_ada = 0

            for kartu in kartu_artikel:
                judul_elemen = kartu.find(['h2', 'h3'])
                if judul_elemen:
                    judul = judul_elemen.text.strip()
                    link = kartu['href']
                    if not link.startswith('http'):
                        link = f"https://www.therundown.ai{link}"
                    
                    if len(judul) > 15 and "/articles/" in link:
                        artikel_ditemukan_di_halaman_ini = True
                        
                        # LOGIKA REM OTOMATIS
                        if link in existing_links:
                            jumlah_artikel_sudah_ada += 1
                        else:
                            if not any(b['link'] == link for b in semua_berita):
                                semua_berita.append({"judul": judul, "link": link})

            if jumlah_artikel_sudah_ada >= 3:
                print(f"\n✋ Menemukan artikel lama di Halaman {halaman}. Pencarian ke masa lalu dihentikan.")
                pencarian_selesai = True
                break

            if not artikel_ditemukan_di_halaman_ini:
                print(f"\n[!] Struktur web berubah atau tidak ada artikel valid di halaman {halaman}.")
                break

            halaman += 1
            # JEDA ACAK MANUSIAWI (3 hingga 7 detik)
            time.sleep(random.uniform(3, 7)) 
            
        except Exception as e:
            print(f"\n[!] Terjadi error sistem: {e}")
            break

    print(f"\n\nDitemukan {len(semua_berita)} kandidat berita baru. Mulai Deep Scrape...")
    print("-" * 70)

    berita_final = []
    
    for i, berita in enumerate(semua_berita, 1):
        print(f"[{i}/{len(semua_berita)}] Deep Scrape: {berita['judul'][:30]}...")
        
        detail_data = ekstrak_detail_rundown(berita['link'], headers)
        tanggal_paling_benar = detail_data.get('tanggal_akurat') or datetime.now().strftime("%Y-%m-%d")
        
        objek_waktu, _ = standarisasi_tanggal_en(tanggal_paling_benar)
        if objek_waktu < batas_waktu_kadaluarsa:
            print(f"      Lewati! Berita terlalu tua ({tanggal_paling_benar}).")
            # Jika menemukan artikel lebih dari 5 bulan, kita juga langsung hentikan looping
            break 
            
        print(f"      Lolos! Tanggal: {tanggal_paling_benar}")
        
        berita_harmonis = {
            "judul": berita['judul'],
            "tanggal": tanggal_paling_benar,
            "link": berita['link'],
            "gambar": detail_data['gambar'],
            "isi_berita": detail_data['isi_berita'],
            "sumber": "The Rundown AI",
            "kategori_bisnis": "AI & Data Infrastruktur"
        }
        
        berita_final.append(berita_harmonis)
        # JEDA ACAK MANUSIAWI SAAT DEEP SCRAPE
        time.sleep(random.uniform(2, 5))

    nama_file = "data/insight_ai_rundown_full.json"
    with open(nama_file, 'w', encoding='utf-8') as f:
        json.dump(berita_final, f, indent=4, ensure_ascii=False)
    
    print("=" * 70)
    print(f"🎯 BINGO! {len(berita_final)} berita The Rundown AI berhasil diamankan dengan aman!")

if __name__ == "__main__":
    main()