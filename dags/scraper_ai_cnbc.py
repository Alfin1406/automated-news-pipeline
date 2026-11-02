import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine, inspect

# --- KONEKSI POSTGRESQL (DOCKER BRIDGE) ---
DATABASE_URL = "postgresql+psycopg2://postgres:alfin1406@host.docker.internal:5432/pln_intelligence_db"
engine = create_engine(DATABASE_URL)

def bersihkan_teks(teks):
    teks = re.sub(r'(?i)baca juga:?.*?(?=\n|$)', '', teks)
    teks = re.sub(r'(?i)scroll to resume content', '', teks)
    teks = re.sub(r'(?i)simak video:?.*?(?=\n|$)', '', teks)
    teks = re.sub(r'(?i)adverstisement', '', teks)
    teks = re.sub(r'\s+', ' ', teks).strip()
    return teks

def standarisasi_tanggal(tgl_str):
    kamus_bulan = {
        'jan': 1, 'januari': 1, 'feb': 2, 'februari': 2, 'mar': 3, 'maret': 3,
        'apr': 4, 'april': 4, 'mei': 5, 'jun': 6, 'juni': 6, 'jul': 7, 'juli': 7,
        'agu': 8, 'agustus': 8, 'sep': 9, 'september': 9, 'okt': 10, 'oktober': 10,
        'nov': 11, 'november': 11, 'des': 12, 'desember': 12
    }
    if not tgl_str:
        return datetime.now(), datetime.now().strftime("%Y-%m-%d")

    tgl_str = tgl_str.lower().strip()
    pola_meta = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', tgl_str)
    if pola_meta:
        tahun, bulan, hari = int(pola_meta.group(1)), int(pola_meta.group(2)), int(pola_meta.group(3))
        try:
            objek_waktu = datetime(tahun, bulan, hari)
            return objek_waktu, objek_waktu.strftime("%Y-%m-%d")
        except ValueError:
            pass

    pola_teks = re.search(r'(\d{1,2})\s+([a-z]+)\s+(\d{4})', tgl_str)
    if pola_teks:
        hari, kata_bulan, tahun = int(pola_teks.group(1)), pola_teks.group(2), int(pola_teks.group(3))
        angka_bulan = kamus_bulan.get(kata_bulan) or kamus_bulan.get(kata_bulan[:3], 1)
        try:
            objek_waktu = datetime(tahun, angka_bulan, hari)
            return objek_waktu, objek_waktu.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return datetime.now(), datetime.now().strftime("%Y-%m-%d")

def ekstrak_detail_cnbc(url, headers):
    hasil = {"isi_berita": "Gagal mengekstrak isi teks.", "gambar": "https://via.placeholder.com/600x400?text=Tidak+Ada+Gambar", "tanggal_akurat": None}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        div_isi = soup.find('div', class_='detail_text') or soup.find('div', class_='detail_wrap') or soup.find('article')
        if div_isi:
            paragraf = div_isi.find_all('p')
            if paragraf:
                teks_kotor = " ".join([p.text.strip() for p in paragraf if p.text])
                hasil["isi_berita"] = bersihkan_teks(teks_kotor)
        
        elemen_gambar = soup.find('meta', property='og:image')
        if elemen_gambar and elemen_gambar.get('content'):
            img_url = elemen_gambar.get('content')
            if img_url.startswith('http') and len(img_url) > 10:
                hasil["gambar"] = img_url
                
        meta_date = soup.find('meta', attrs={'name': 'publishdate'}) or soup.find('meta', property='article:published_time')
        if meta_date and meta_date.get('content'):
            _, tgl_benar = standarisasi_tanggal(meta_date.get('content'))
            hasil["tanggal_akurat"] = tgl_benar
        else:
            elemen_tgl_detail = soup.find(class_='date')
            if elemen_tgl_detail:
                _, tgl_benar = standarisasi_tanggal(elemen_tgl_detail.text.strip())
                hasil["tanggal_akurat"] = tgl_benar
    except Exception:
        pass
    return hasil

def main():
    TARGET_BULAN_MUNDUR = 5
    batas_waktu_kadaluarsa = datetime.now() - timedelta(days=TARGET_BULAN_MUNDUR * 30)

    print(f"🚀 Membangun Pipeline: Scraper 1 (CNBC Tech - Tag AI)")
    print(f"Batas Kadaluarsa: {batas_waktu_kadaluarsa.strftime('%Y-%m-%d')}")
    print("=" * 70)

    # --- LOGIKA INCREMENTAL (CEK DB) ---
    existing_links = set()
    try:
        inspector = inspect(engine)
        if inspector.has_table('tabel_berita_ai'):
            df_existing = pd.read_sql("SELECT link FROM tabel_berita_ai WHERE sumber='CNBC Tech'", con=engine)
            existing_links = set(df_existing['link'].tolist())
            print(f"✅ Ditemukan {len(existing_links)} artikel CNBC lama di Database.")
    except Exception as e:
        print(f"⚠️ Peringatan DB: {e}")

    semua_berita = []
    halaman = 1
    halaman_maksimal = 100 
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
    pencarian_selesai = False

    while halaman <= halaman_maksimal and not pencarian_selesai:
        url = "https://www.cnbcindonesia.com/tag/artificial-intelligence" if halaman == 1 else f"https://www.cnbcindonesia.com/tag/artificial-intelligence/{halaman}"
        print(f" -> Memeriksa halaman {halaman}...", end='\r')
        
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            list_artikel = soup.find_all('article')
            if not list_artikel:
                list_artikel = [li for li in soup.find_all('li') if li.find('h2')]
            if not list_artikel:
                break

            artikel_kadaluarsa_di_halaman_ini = 0
            artikel_sudah_ada = 0

            for artikel in list_artikel:
                elemen_judul = artikel.find('h2')
                elemen_link = artikel.find('a')
                elemen_tanggal = artikel.find(class_=re.compile(r'(date|label)')) 

                if elemen_judul and elemen_link:
                    judul = elemen_judul.text.strip()
                    link = elemen_link['href']
                    tanggal_mentah = elemen_tanggal.text.strip() if elemen_tanggal else ""
                    
                    # 1. Rem Database (Prioritas)
                    if link in existing_links:
                        artikel_sudah_ada += 1
                        if artikel_sudah_ada >= 3:
                            print(f"\n✋ Menemukan artikel lama di Halaman {halaman}. Pencarian dihentikan.")
                            pencarian_selesai = True
                            break
                        continue

                    # 2. Rem Waktu Maksimal
                    objek_waktu, tanggal_seragam = standarisasi_tanggal(tanggal_mentah)
                    if objek_waktu < batas_waktu_kadaluarsa:
                        artikel_kadaluarsa_di_halaman_ini += 1
                        if artikel_kadaluarsa_di_halaman_ini >= 5:
                            pencarian_selesai = True
                            break
                        continue 

                    if not any(b['link'] == link for b in semua_berita):
                        semua_berita.append({
                            "judul": judul, "link": link, 
                            "tanggal_mentah": tanggal_mentah, "tanggal_seragam": tanggal_seragam
                        })

            halaman += 1
            time.sleep(1) 

        except Exception as e:
            print(f"\nTerjadi error saat mengakses halaman {halaman}: {e}")
            break

    print(f"\n\nDitemukan {len(semua_berita)} kandidat berita Super-Relevan. Mulai Deep Scrape...")
    print("-" * 70)

    berita_final = []
    for i, berita in enumerate(semua_berita, 1):
        print(f"[{i}/{len(semua_berita)}] Ekstrak & Bersihkan Teks: {berita['judul'][:30]}...")
        detail_data = ekstrak_detail_cnbc(berita['link'], headers)
        
        tanggal_paling_benar = detail_data.get('tanggal_akurat') or berita['tanggal_seragam']
            
        berita_harmonis = {
            "judul": berita['judul'],
            "tanggal": tanggal_paling_benar,
            "link": berita['link'],
            "gambar": detail_data['gambar'],
            "isi_berita": detail_data['isi_berita'],
            "sumber": "CNBC Tech",
            "kategori_bisnis": "AI & Data Infrastruktur"
        }
        
        berita_final.append(berita_harmonis)
        time.sleep(1)

    import os
    os.makedirs("data", exist_ok=True)
    nama_file = "data/insight_ai_cnbc_full.json"
    with open(nama_file, 'w', encoding='utf-8') as f:
        json.dump(berita_final, f, indent=4, ensure_ascii=False)
    
    print("=" * 70)
    print(f"🎯 BINGO! {len(berita_final)} berita CNBC bersih siap diproses oleh AI!")

if __name__ == "__main__":
    main()