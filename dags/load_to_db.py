import os
import time
import json
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

# ==============================================================
# 1. SETUP KONEKSI DATABASE NEON DENGAN FITUR RETRY
# ==============================================================
def get_engine_with_retry(max_retries=5):
    # Mengambil kredensial dari Environment Variables sesuai standar tim
    db_host = os.getenv("POSTGRES_HOST")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB")
    db_user = os.getenv("POSTGRES_USER")
    db_pass = os.getenv("POSTGRES_PASSWORD")
    db_ssl = os.getenv("POSTGRES_SSLMODE", "require")

    if not all([db_host, db_name, db_user, db_pass]):
        raise ValueError("Environment variables untuk database Neon belum disetel di Airflow!")

    database_url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?sslmode={db_ssl}"

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Mencoba koneksi ke Neon DB ({attempt}/{max_retries})...")
            # Menambahkan timeout agar tidak hang
            engine = create_engine(database_url, connect_args={"connect_timeout": 20})
            
            # Test koneksi ringan
            with engine.connect() as conn:
                print("✅ Koneksi Neon berhasil!")
            return engine
            
        except Exception as e:
            print(f"❌ Koneksi gagal: {e}")
            if attempt == max_retries:
                raise
            
            wait_time = 15 * attempt
            print(f"Mencoba kembali dalam {wait_time} detik...")
            time.sleep(wait_time)

# ==============================================================
# 2. PROSES UTAMA (ETL)
# ==============================================================
def main():
    # Gunakan absolute path agar aman saat dijalankan oleh Airflow Docker
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'data', 'berita_new_enriched.json')

    print(f"Membaca file {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ File JSON tidak ditemukan. Pastikan task scraper berjalan sukses sebelumnya.")
        return

    if not data:
        print("ℹ️ Tidak ada data untuk dimasukkan ke database.")
        return

    # Transformasi Data Pandas
    df = pd.DataFrame(data)
    df = df.drop_duplicates(subset=['link']) 
    df['tanggal'] = pd.to_datetime(df['tanggal']).dt.date

    if 'teknologi_dibahas' in df.columns:
        df['teknologi_dibahas'] = df['teknologi_dibahas'].apply(
            lambda x: [i.strip() for i in x.split(',')] if isinstance(x, str) else x
        )

    print("Memulai proses UPSERT ke database Neon...")
    data_to_insert = df.to_dict(orient='records')
    
    # Panggil engine yang sudah dilengkapi fitur retry
    engine = get_engine_with_retry()
    
    with engine.begin() as connection:
        berita_diproses = 0
        
        for baris in data_to_insert:
            array_str = "{" + ",".join([f'"{t}"' for t in baris.get('teknologi_dibahas', [])]) + "}" if baris.get('teknologi_dibahas') else "{}"
            
            # Mengubah DO NOTHING menjadi UPSERT (DO UPDATE) standar tim Arza
            query = text("""
                INSERT INTO tabel_berita_ai (
                    judul, tanggal, link, gambar, isi_berita, 
                    sumber, kategori_bisnis, ringkasan_ai, 
                    teknologi_dibahas, kategori_lisensi, skor_relevansi_it,
                    waktu_scrape
                ) VALUES (
                    :judul, :tanggal, :link, :gambar, :isi_berita, 
                    :sumber, :kategori_bisnis, :ringkasan_ai, 
                    CAST(:teknologi_dibahas AS text[]), :kategori_lisensi, :skor_relevansi_it,
                    :waktu_scrape
                )
                ON CONFLICT (link) DO UPDATE SET
                    judul = EXCLUDED.judul,
                    tanggal = EXCLUDED.tanggal,
                    gambar = EXCLUDED.gambar,
                    isi_berita = EXCLUDED.isi_berita,
                    sumber = EXCLUDED.sumber,
                    kategori_bisnis = EXCLUDED.kategori_bisnis,
                    ringkasan_ai = EXCLUDED.ringkasan_ai,
                    teknologi_dibahas = EXCLUDED.teknologi_dibahas,
                    kategori_lisensi = EXCLUDED.kategori_lisensi,
                    skor_relevansi_it = EXCLUDED.skor_relevansi_it,
                    waktu_scrape = EXCLUDED.waktu_scrape
            """)
            
            connection.execute(query, {
                "judul": baris.get('judul', ''),
                "tanggal": baris.get('tanggal'),
                "link": baris['link'],
                "gambar": baris.get('gambar', ''),
                "isi_berita": baris.get('isi_berita', ''),
                "sumber": baris.get('sumber', ''),
                "kategori_bisnis": baris.get('kategori_bisnis', ''),
                "ringkasan_ai": baris.get('ringkasan_ai', ''),
                "teknologi_dibahas": array_str,
                "kategori_lisensi": baris.get('kategori_lisensi', ''),
                "skor_relevansi_it": baris.get('skor_relevansi_it', 0),
                "waktu_scrape": datetime.now()
            })
            berita_diproses += 1

    print(f"✅ Proses True Incremental Load (UPSERT) Selesai!")
    print(f"📊 Statistik: Berhasil memproses {berita_diproses} berita ke Neon DB.")

if __name__ == "__main__":
    main()