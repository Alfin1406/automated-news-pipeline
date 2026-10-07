import os
import json
import pandas as pd
from sqlalchemy import create_engine
import google.generativeai as genai
import time
import re

# --- 1. KONFIGURASI GEMINI AI ---
API_KEY_GEMINI = os.getenv("GEMINI_API_KEY")

if not API_KEY_GEMINI:
    print("⚠️ ERROR: GEMINI_API_KEY tidak ditemukan di environment variables!")

genai.configure(api_key=API_KEY_GEMINI)
model = genai.GenerativeModel('gemini-3.1-flash-lite') 

# --- 2. KONEKSI POSTGRESQL ---
DATABASE_URL = "postgresql+psycopg2://postgres:alfin1406@host.docker.internal:5432/pln_intelligence_db"
engine = create_engine(DATABASE_URL)

# --- 3. FUNGSI ANALISIS AI (HEMAT TOKEN) ---
def analisis_artikel_dengan_gemini(isi_teks):
    """Hanya meminta Gemini mengekstrak Lisensi dan Teknologi. Ringkasan di-handle oleh Python murni."""
    
    if not isi_teks or len(str(isi_teks)) < 50:
        return {
            "teknologi_dibahas": "-",
            "kategori_lisensi": "Tidak Diketahui"
        }

    teks_potong = str(isi_teks)[:3000]
    
    # Prompt diubah: Fitur "ringkasan_ai" dihapus agar AI tidak membuang token untuk mengetik paragraf panjang
    prompt = f"""
    Kamu adalah Analis Data di PLN Icon Plus. Analisis teks artikel berita berikut ini:
    
    "{teks_potong}"
    
    Berikan hasil analisis HANYA dalam format JSON persis seperti struktur di bawah ini tanpa tambahan teks apa pun:
    {{
        "teknologi_dibahas": "Sebutkan nama spesifik model AI, platform, atau teknologi infrastruktur utama yang dibahas (misal: Llama 3, ChatGPT, Nvidia GPU, AWS, Hugging Face). Jika banyak, pisahkan dengan koma. Jika tidak ada, isi dengan '-'.",
        "kategori_lisensi": "Berdasarkan teknologi yang dibahas, klasifikasikan menjadi salah satu: 'Komersil', 'Open Source', atau 'Campuran/Tidak Diketahui'."
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        hasil_bersih = response.text.replace('```json', '').replace('```', '').strip()
        hasil_dict = json.loads(hasil_bersih)
        return hasil_dict
    except Exception as e:
        print(f"    [!] Gagal memproses AI: {e}")
        return {
            "teknologi_dibahas": "-",
            "kategori_lisensi": "Error"
        }

# --- 4. PROSES UTAMA MIGRASI & ENRICHMENT ---
def main():
    berita_gabungan = []

    for file_json in ['data/insight_ai_cnbc_full.json', 'data/insight_ai_detik_full.json']:
        try:
            with open(file_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                berita_gabungan.extend(data)
        except FileNotFoundError:
            print(f"File {file_json} tidak ditemukan. Dilewati.")

    if not berita_gabungan:
        print("Tidak ada data untuk dimigrasikan.")
        return

    print(f"Memulai proses AI Enrichment untuk {len(berita_gabungan)} artikel...")
    print("-" * 70)

    for i, berita in enumerate(berita_gabungan, 1):
        print(f"[{i}/{len(berita_gabungan)}] Memproses: {berita['judul'][:40]}...")
        
        isi_teks = berita.get('isi_berita', '')
        
        # 1. LOGIKA PYTHON MURNI (Gratis): Ambil ~250 karakter pertama sebagai preview/ringkasan
        if len(isi_teks) > 250:
            ringkasan_hemat = isi_teks[:250].rsplit(' ', 1)[0] + "..."
        else:
            ringkasan_hemat = isi_teks
            
        berita['ringkasan_ai'] = ringkasan_hemat
        
        # 2. LOGIKA GEMINI AI (Hemat Token): Hanya mengambil 2 entitas data
        insight_ai = analisis_artikel_dengan_gemini(isi_teks)
        
        berita['teknologi_dibahas'] = insight_ai.get('teknologi_dibahas', '-')
        berita['kategori_lisensi'] = insight_ai.get('kategori_lisensi', 'Tidak Diketahui')
        
        time.sleep(5) 

    print("-" * 70)
    print("Menyimpan ke PostgreSQL...")
    
    df = pd.DataFrame(berita_gabungan)
    
    if 'isi_berita' in df.columns:
        df = df.drop(columns=['isi_berita'])
        
    df.to_sql('tabel_berita_ai', engine, if_exists='replace', index=False)
    print(f"Sukses! {len(df)} artikel telah diproses dan dimasukkan ke PostgreSQL 'tabel_berita_ai'.")

if __name__ == "__main__":
    main()