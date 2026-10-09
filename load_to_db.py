import json
import pandas as pd
from sqlalchemy import create_engine, text # Tambahkan import 'text'
from sqlalchemy.types import String, Text, Integer, Date
from sqlalchemy.dialects.postgresql import ARRAY 

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
    # Hapus duplikat di dalam file JSON itu sendiri
    df = df.drop_duplicates(subset=['link']) 
    df['tanggal'] = pd.to_datetime(df['tanggal']).dt.date

    if 'teknologi_dibahas' in df.columns:
        df['teknologi_dibahas'] = df['teknologi_dibahas'].apply(
            lambda x: [i.strip() for i in x.split(',')] if isinstance(x, str) else x
        )

    print("Memulai True Incremental Load ke database...")
    
    # 1. Konversi DataFrame ke List of Dictionaries
    data_to_insert = df.to_dict(orient='records')
    
    # 2. Buka koneksi langsung (raw connection)
    with engine.begin() as connection:
        berita_baru = 0
        berita_duplikat = 0
        
        # 3. Looping untuk insert satu per satu dengan proteksi duplikasi
        for baris in data_to_insert:
            # Mengubah format list python ke format array postgres literal "{a,b,c}"
            # Ini sangat penting agar PostgreSQL tidak error saat menerima Array
            array_str = "{" + ",".join([f'"{t}"' for t in baris['teknologi_dibahas']]) + "}" if baris['teknologi_dibahas'] else "{}"
            
            query = text("""
                INSERT INTO tabel_berita_ai (
                    judul, tanggal, link, gambar, isi_berita, 
                    sumber, kategori_bisnis, ringkasan_ai, 
                    teknologi_dibahas, kategori_lisensi, skor_relevansi_it
                ) VALUES (
                    :judul, :tanggal, :link, :gambar, :isi_berita, 
                    :sumber, :kategori_bisnis, :ringkasan_ai, 
                    CAST(:teknologi_dibahas AS text[]), :kategori_lisensi, :skor_relevansi_it
                )
                ON CONFLICT (link) DO NOTHING
            """)
            
            # Eksekusi dan tangkap hasilnya (apakah baris dimasukkan atau di-skip)
            result = connection.execute(query, {
                "judul": baris.get('judul', ''),
                "tanggal": baris.get('tanggal'),
                "link": baris['link'],
                "gambar": baris.get('gambar', ''),
                "isi_berita": baris.get('isi_berita', ''),
                "sumber": baris.get('sumber', ''),
                "kategori_bisnis": baris.get('kategori_bisnis', ''),
                "ringkasan_ai": baris.get('ringkasan_ai', ''),
                "teknologi_dibahas": array_str, # Menggunakan string literal array
                "kategori_lisensi": baris.get('kategori_lisensi', ''),
                "skor_relevansi_it": baris.get('skor_relevansi_it', 0)
            })
            
            # Cek jika ada baris yang terpengaruh (artinya berhasil masuk)
            if result.rowcount > 0:
                berita_baru += 1
            else:
                berita_duplikat += 1

    print(f"✅ True Incremental Load Selesai!")
    print(f"📊 Statistik: Masuk {berita_baru} berita baru | Menolak {berita_duplikat} berita lama (duplikat).")

if __name__ == "__main__":
    main()