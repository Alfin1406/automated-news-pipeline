import json
import requests
from bs4 import BeautifulSoup
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
    teks = re.sub(r'(?i)scroll to continue with content', '', teks)
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

def ekstrak_detail_detik(url, headers):
    hasil = {"isi_berita": "Gagal mengekstrak isi teks.", "tanggal_mentah": "Tanggal tidak diketahui", "gambar": "https://via.placeholder.com/600x400?text=No+Image"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        div_isi = soup.find('div', class_='detail__body-text')
        if div_isi:
            paragraf = div_isi.find_all('p')
            if paragraf:
                teks_kotor = " ".join([p.text.strip() for p in paragraf])
                hasil["isi_berita"] = bersihkan_teks(teks_kotor)
        
        elemen_tanggal = soup.find('div', class_='detail__date')
        if elemen_tanggal:
            hasil["tanggal_mentah"] = elemen_tanggal.text.strip()
        else:
            meta_date = soup.find('meta', attrs={'name': 'publishdate'})
            if meta_date:
                hasil["tanggal_mentah"] = meta_date.get('content', "")

        elemen_gambar = soup.find('meta', property='og:image')
        if elemen_gambar:
            hasil["gambar"] = elemen_gambar.get('content', hasil["gambar"])
    except Exception:
        pass
    return hasil

def main():
    TARGET_BULAN_MUNDUR = 5
    batas_waktu_kadaluarsa = datetime.now() - timedelta(days=TARGET_BULAN_MUNDUR * 30)

    print(f"🚀 Membangun Pipeline: Scraper 2 (Detik Inet - Tag AI)")
    print(f"Batas Kadaluarsa: {batas_waktu_kadaluarsa.strftime('%Y-%m-%d')}")
    print("=" * 70)

    # --- LOGIKA INCREMENTAL (CEK DB) ---
    existing_links = set()
    try:
        inspector = inspect(engine)
        if inspector.has_table('tabel_berita_ai'):
            df_existing = pd.read_sql("SELECT link FROM tabel_berita_ai WHERE sumber='Detik Inet'", con=engine)
            existing_links = set(df_existing['link'].tolist())
            print(f"✅ Ditemukan {len(existing_links)} artikel Detik lama di Database.")
    except Exception as e:
        print(f"⚠️ Peringatan DB: {e}")

    semua_berita = []
    halaman = 1
    halaman_maksimal = 100 
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'}
    pencarian_selesai = False

    print("TAHAP 1: Menjelajahi halaman Tag AI untuk mencari kandidat...")
    while halaman <= halaman_maksimal and not pencarian_selesai:
        url = f"https://www.detik.com/tag/artificial-intelligence/?sortby=time&page={halaman}"
        print(f"  -> Memeriksa halaman {halaman}...", end='\r')
        
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            list_artikel = soup.find_all('article')
            
            if not list_artikel:
                break 

            artikel_kadaluarsa_di_halaman_ini = 0
            artikel_sudah_ada = 0

            for artikel in list_artikel:
                a_tag = artikel.find('a')
                if not a_tag or 'href' not in a_tag.attrs:
                    continue
                    
                judul_elemen = artikel.find('h2') or artikel.find('h3')
                if not judul_elemen:
                    continue
                    
                judul = judul_elemen.text.strip()
                link = a_tag['href']
                
                # 1. Rem Database
                if link in existing_links:
                    artikel_sudah_ada += 1
                    if artikel_sudah_ada >= 3:
                        print(f"\n✋ Menemukan artikel lama di Halaman {halaman}. Pencarian dihentikan.")
                        pencarian_selesai = True
                        break
                    continue
                
                # 2. Rem Waktu
                elemen_tgl = artikel.find(class_=re.compile('date'))
                if elemen_tgl:
                    obj_waktu, _ = standarisasi_tanggal(elemen_tgl.text.strip())
                    if obj_waktu < batas_waktu_kadaluarsa:
                        artikel_kadaluarsa_di_halaman_ini += 1
                        if artikel_kadaluarsa_di_halaman_ini >= 5:
                            pencarian_selesai = True
                            break
                        continue 
                        
                if not any(b['link'] == link for b in semua_berita):
                    semua_berita.append({"judul": judul, "link": link})

            halaman += 1
            time.sleep(1) 

        except Exception as e:
            break

    print(f"\n\nDitemukan {len(semua_berita)} kandidat berita Super-Relevan. Mulai Deep Scrape...")
    print("-" * 70)

    berita_final = []
    for i, berita in enumerate(semua_berita, 1):
        print(f"[{i}/{len(semua_berita)}] Deep Scrape & Cek Tanggal: {berita['judul'][:30]}...")
        
        detail_data = ekstrak_detail_detik(berita['link'], headers)
        objek_waktu, tanggal_seragam = standarisasi_tanggal(detail_data['tanggal_mentah'])
        
        if objek_waktu < batas_waktu_kadaluarsa:
            print(f"      Lewati! Berita terlalu tua ({tanggal_seragam}).")
            continue 
            
        print(f"      Lolos! Tanggal: {tanggal_seragam}")
        
        berita_harmonis = {
            "judul": berita['judul'],
            "tanggal": tanggal_seragam, 
            "link": berita['link'],
            "gambar": detail_data['gambar'],
            "isi_berita": detail_data['isi_berita'],
            "sumber": "Detik Inet",
            "kategori_bisnis": "AI & Data Infrastruktur"
        }
        
        berita_final.append(berita_harmonis)
        time.sleep(1) 

    import os
    os.makedirs("data", exist_ok=True)
    nama_file = "data/insight_ai_detik_full.json"
    with open(nama_file, 'w', encoding='utf-8') as f:
        json.dump(berita_final, f, indent=4, ensure_ascii=False)
    
    print("=" * 70)
    print(f"🎯 BINGO! {len(berita_final)} berita Detik bersih siap diproses oleh AI!")

if __name__ == "__main__":
    main()