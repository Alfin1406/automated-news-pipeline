import json
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.types import String, Text, Integer, Date
from sqlalchemy.dialects.postgresql import ARRAY # Import modul khusus Array PostgreSQL

DATABASE_URL = "postgresql+psycopg2://postgres:alfin1406@host.docker.internal:5432/pln_intelligence_db"
engine = create_engine(DATABASE_URL)

def main():
    print("Membaca file data/berita_new_enriched.json...")
    try:
        with open('data/berita_new_enriched.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("File JSON tidak ditemukan.")
        return

    if not data:
        print("Tidak ada data untuk dimasukkan ke database.")
        return

    df = pd.DataFrame(data)
    df = df.drop_duplicates(subset=['link'])
    df['tanggal'] = pd.to_datetime(df['tanggal']).dt.date

    # KONVERSI STRING DIPISAH KOMA MENJADI LIST PYTHON (UNTUK ARRAY POSTGRESQL)
    if 'teknologi_dibahas' in df.columns:
        df['teknologi_dibahas'] = df['teknologi_dibahas'].apply(
            lambda x: [i.strip() for i in x.split(',')] if isinstance(x, str) else x
        )

    # SKEMA DATABASE DENGAN ARRAY & INTEGER STANDAR INDUSTRI
    skema_database = {
        'judul': Text(),
        'tanggal': Date(),
        'link': String(255),
        'gambar': Text(),
        'isi_berita': Text(),
        'sumber': String(50),
        'kategori_bisnis': String(100),
        'ringkasan_ai': Text(),
        'teknologi_dibahas': ARRAY(Text()),    # <-- ARRAY POSTGRESQL YANG PRESISI!
        'kategori_lisensi': String(50),
        'skor_relevansi_it': Integer()         # <-- INTEGER BIASA (BUKAN BIGINT)
    }

    print("Memasukkan data ke database dengan skema Array dan Integer standar...")
    
    # MENGGUNAKAN APPEND & DTYPE AGAR TIPE DATA TIDAK BERUBAH OLEH PANDAS
    df.to_sql('tabel_berita_ai', con=engine, if_exists='append', index=False, dtype=skema_database)
    
    print(f"✅ BINGO! {len(df)} data berhasil dimasukkan. Kolom teknologi berwujud ARRAY dan skor berwujud INT.")

if __name__ == "__main__":
    main()