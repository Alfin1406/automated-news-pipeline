import os
import json
import pandas as pd
from sqlalchemy import create_engine, inspect

# --- KONEKSI POSTGRESQL ---
DATABASE_URL = "postgresql+psycopg2://postgres:alfin1406@host.docker.internal:5432/pln_intelligence_db"
engine = create_engine(DATABASE_URL)

# ==========================================
# KAMUS KATA KUNCI (BILINGUAL ID & EN)
# ==========================================
KAMUS_TOPIK = {
    "Technology": ["ai", "artificial intelligence", "kecerdasan buatan", "machine learning", "algoritma", "model bahasa", "llm", "neural network", "deep learning"],
    "Infrastructure": ["data center", "pusat data", "cloud", "server", "gpu", "nvidia", "komputasi", "jaringan", "infrastruktur", "compute", "chips", "semiconductor"],
    "Energy": ["air", "listrik", "pln", "energi", "karbon", "pembangkit", "jatiluhur", "ramah lingkungan", "emisi", "energy", "power", "nuclear", "grid", "emission"],
    "Investment": ["investasi", "triliun", "miliar", "dana", "saham", "startup", "akuisisi", "proyek", "investor", "ekonomi", "investment", "funding", "billion", "million", "acquisition", "valuation"]
}

KAMUS_LISENSI = {
    "Open Source": ["open source", "llama", "hugging face", "mistral", "sumber terbuka", "gratis", "komunitas", "open-source", "open weights"],
    "Komersil": ["chatgpt", "openai", "gemini", "claude", "berbayar", "langganan", "lisensi", "microsoft", "aws", "google cloud", "anthropic", "enterprise"]
}

def proses_tanpa_ai(isi_teks):
    """
    Mengklasifikasikan teks menggunakan pencocokan kata kunci
    """
    if not isi_teks:
        return {"topik_dibahas": [], "kategori_lisensi": "Tidak Diketahui", "skor_relevansi_it": 0}

    teks_lower = str(isi_teks).lower()
    
    # --- LOGIKA 1: EKSTRAK TOPIK ---
    topik_ditemukan = []
    for topik, kata_kunci in KAMUS_TOPIK.items():
        if any(k in teks_lower for k in kata_kunci):
            topik_ditemukan.append(topik)
            
    # --- LOGIKA 2: TENTUKAN LISENSI ---
    skor_open_source = sum(teks_lower.count(k) for k in KAMUS_LISENSI["Open Source"])
    skor_komersil = sum(teks_lower.count(k) for k in KAMUS_LISENSI["Komersil"])
    
    lisensi = "Tidak Diketahui"
    if skor_open_source > skor_komersil:
        lisensi = "Open Source"
    elif skor_komersil > skor_open_source:
        lisensi = "Komersil"
    elif skor_open_source > 0 and skor_open_source == skor_komersil:
        lisensi = "Campuran"

    # --- LOGIKA 3: THRESHOLD RELEVANSI IT ---
    skor_relevansi = sum(teks_lower.count(k) for k in KAMUS_TOPIK["Infrastructure"]) * 10
    skor_relevansi += sum(teks_lower.count(k) for k in KAMUS_TOPIK["Technology"]) * 5
    skor_relevansi = min(skor_relevansi, 100)

    # PERUBAHAN ARRAY: topik_ditemukan dikembalikan langsung sebagai List []
    return {
        "topik_dibahas": topik_ditemukan if topik_ditemukan else [],
        "kategori_lisensi": lisensi,
        "skor_relevansi_it": skor_relevansi
    }

def main():
    print("⚡ Memulai Microservice: Transformasi Data (Rule-Based NLP)")
    print("=" * 70)

    berita_gabungan = []
    path_data_cnbc = 'data/insight_ai_cnbc_full.json'
    path_data_detik = 'data/insight_ai_detik_full.json'
    path_data_rundown = 'data/insight_ai_rundown_full.json'

    for file_json in [path_data_cnbc, path_data_detik, path_data_rundown]:
        if os.path.exists(file_json):
            with open(file_json, 'r', encoding='utf-8') as f:
                berita_gabungan.extend(json.load(f))

    if not berita_gabungan:
        print("Tidak ada data hasil scraping.")
        return

    # Kita lewati dulu proses filter existing link agar semua data diproses ulang ke format array
    # Karena kita akan me-replace seluruh tabel database.
    berita_baru = berita_gabungan
    print(f"📊 Memproses ulang {len(berita_baru)} artikel ke format Array...")
    print("-" * 70)

    berita_lolos_filter = []

    for i, berita in enumerate(berita_baru, 1):
        isi_teks = berita.get('isi_berita', '')
        berita['ringkasan_ai'] = isi_teks[:250].rsplit(' ', 1)[0] + "..." if len(isi_teks) > 250 else isi_teks
            
        hasil_ekstrak = proses_tanpa_ai(isi_teks)
        
        berita['teknologi_dibahas'] = hasil_ekstrak['topik_dibahas']
        berita['kategori_lisensi'] = hasil_ekstrak['kategori_lisensi']
        berita['skor_relevansi_it'] = hasil_ekstrak['skor_relevansi_it']
        
        if berita['skor_relevansi_it'] >= 15:
            berita_lolos_filter.append(berita)

    print("-" * 70)
    print(f"🎯 Dari {len(berita_baru)} artikel, {len(berita_lolos_filter)} berbobot IT dan lolos filter.")

    path_output = 'data/berita_new_enriched.json'
    with open(path_output, 'w', encoding='utf-8') as f:
        json.dump(berita_lolos_filter, f, indent=4, ensure_ascii=False)
    
    print("✅ Selesai! File JSON baru dengan format Array siap.")

if __name__ == "__main__":
    main()