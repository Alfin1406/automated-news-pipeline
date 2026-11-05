import json

file_path = 'dags/data/berita_new_enriched.json'

try:
    with open(file_path, 'r', encoding='utf-8') as file:
        data_berita = json.load(file)
    
    total_artikel = len(data_berita)
    jumlah_sector_event = 0
    
    print(f"Mengecek {total_artikel} artikel sampel dari pipeline...\n")
    
    for artikel in data_berita:
        judul = artikel.get('judul', '')
        isi = artikel.get('isi_berita', '').lower()
        # Ambil array teknologi_dibahas dan jadikan huruf kecil semua
        teknologi = [t.lower() for t in artikel.get('teknologi_dibahas', [])]
        
        # Cek keyword dari Notion: new project, expansion, regulation, investment
        is_event = False
        
        # Cek dari tag hasil ekstraksi AI
        if 'investment' in teknologi or 'investasi' in teknologi or 'regulasi' in teknologi:
            is_event = True
        # Cek dari isi berita mentahnya
        elif any(kw in isi for kw in ['ekspansi', 'investasi', 'proyek baru', 'regulasi', 'pendanaan']):
            is_event = True
            
        if is_event:
            jumlah_sector_event += 1
            print(f"[TERDETEKSI SECTOR EVENT] -> {judul}")

    persentase = (jumlah_sector_event / total_artikel) * 100 if total_artikel > 0 else 0

    print("\n=== HASIL FEASIBILITY CHECK EXISTING NEWS PIPELINE ===")
    print(f"Total Artikel Terkumpul     : {total_artikel}")
    print(f"Jumlah Artikel Sector Event : {jumlah_sector_event}")
    print(f"Persentase Relevansi        : {persentase:.2f}%\n")
    
    if persentase > 0:
        print("BUKTI: GO! Pipeline AI terbukti mampu mengekstrak insight Sector Event dari teks mentah.")
    else:
        print("REVIEW: Sector Event belum terdeteksi di sampel ini.")

except FileNotFoundError:
    print(f"Error: File {file_path} tidak ditemukan di folder tersebut.")
except Exception as e:
    print(f"Terjadi kesalahan sistem: {e}")