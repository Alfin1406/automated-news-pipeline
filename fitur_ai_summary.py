import streamlit as st
import pandas as pd
import datetime
import google.generativeai as genai

def panggil_gemini_api(teks_berita, subtopic):
    """Fungsi untuk memanggil API Gemini dan mendapatkan ringkasan terstruktur."""
    
    prompt = f"""
    Kamu adalah seorang analis intelijen bisnis profesional. 
    Tugasmu adalah menganalisis berita-berita berikut yang berfokus pada subtopik: {subtopic}.

    Berita:
    {teks_berita}

    Buatkan ringkasan eksekutif dengan struktur persis seperti berikut:
    1. Ringkasan Utama (Paragraf singkat inti situasi)
    2. Tren dan Perkembangan (Poin-poin tren utama)
    3. Perusahaan yang Disebut (Daftar perusahaan dan konteksnya)
    4. Peluang Bisnis (Potensi profit atau investasi)
    5. Risiko dan Hal yang Perlu Dipantau (Ancaman operasional, regulasi, dsb)
    6. Referensi Berita (Daftar judul berita beserta tanggalnya)
    """
    
    try:
        # Menggunakan model gemini-1.5-flash sesuai konfigurasi sistemmu
        model = genai.GenerativeModel('gemini-3.5-flash-lite')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Terjadi kesalahan saat memanggil Gemini API: {e}"

def gabungkan_berita(df):
    """Menggabungkan DataFrame menjadi teks panjang untuk dikonsumsi API."""
    teks = ""
    for index, row in df.iterrows():
        teks += f"- Judul: {row['judul']}\n"
        
        # Format tanggal menjadi string yang aman jika bertipe Timestamp
        tanggal_str = row['tanggal'].strftime('%Y-%m-%d') if hasattr(row['tanggal'], 'strftime') else str(row['tanggal'])
        teks += f"  Tanggal: {tanggal_str}\n"
        teks += f"  Sumber: {row['sumber']}\n"
        
        # Menggunakan .get() agar aman jika nama kolom berbeda
        isi = row.get('isi_berita', row.get('ringkasan', 'Tidak ada isi berita.'))
        teks += f"  Isi: {isi}\n\n"
    return teks

def tampilkan_artikel_pendukung(df):
    """Merender daftar berita dalam format grid 2 kolom."""
    st.write("---")
    st.subheader("📑 Artikel Pendukung")
    
    # Reset index agar pembagian kolom tidak error
    df = df.reset_index(drop=True)
    cols = st.columns(2)
    
    for index, row in df.iterrows():
        col = cols[index % 2]
        with col:
            with st.container(border=True):
                st.markdown(f"**{row['judul']}**")
                
                tanggal_str = row['tanggal'].strftime('%Y-%m-%d') if hasattr(row['tanggal'], 'strftime') else str(row['tanggal'])
                st.caption(f"{row['sumber']} • {tanggal_str}")
                
                # Render tautan baca
                link = row.get('url', '#')
                st.markdown(f"[Baca berita asli ➔]({link})")

def render_fitur_ai_summary(df, daftar_subtopic):
    """
    Fungsi utama UI AI Summary yang akan dipanggil di dashboard utama.
    """
    st.divider()
    st.subheader("🤖 AI Business Analysis: Summary per Subtopic")
    st.caption("Buat ringkasan perkembangan bisnis berdasarkan subtopik dan periode berita yang dipilih.")

    # 1. Setup default value untuk kalender (Hari ini & 14 hari sebelumnya)
    hari_ini = datetime.date.today()
    dua_minggu_lalu = hari_ini - datetime.timedelta(days=14)

    # 2. Render Form UI
    with st.form("form_ai_subtopic"):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            pilihan_subtopic = st.selectbox(
                "Subtopic",
                options=daftar_subtopic
            )
            
        with col2:
            tanggal_awal = st.date_input("Tanggal Awal", value=dua_minggu_lalu)
            
        with col3:
            tanggal_akhir = st.date_input("Tanggal Akhir", value=hari_ini)
            
        generate_btn = st.form_submit_button("Generate AI Summary", type="primary")

    # 3. Logika Pemrosesan setelah tombol diklik
    if generate_btn:
        selisih_hari = (tanggal_akhir - tanggal_awal).days
        
        # Validasi Rentang Waktu (Maks 14 Hari sesuai arahan Mentor)
        if selisih_hari > 14:
            st.error("⚠️ Sesuai limitasi sistem, rentang waktu maksimal untuk AI Summary adalah 14 hari. Silakan perkecil rentang tanggal.")
        elif tanggal_awal > tanggal_akhir:
            st.error("⚠️ Tanggal Awal tidak boleh lebih besar dari Tanggal Akhir.")
        else:
            with st.spinner(f"Gemini sedang menyusun laporan intelijen bisnis untuk '{pilihan_subtopic}'..."):
                
                # Pastikan format tipe data sudah datetime
                df['tanggal'] = pd.to_datetime(df['tanggal'])
                
                # Filter DataFrame berdasarkan tanggal
                mask_tanggal = (df['tanggal'].dt.date >= tanggal_awal) & (df['tanggal'].dt.date <= tanggal_akhir)
                
                # Filter DataFrame berdasarkan Subtopik (Mendukung tipe data Array/List)
                mask_subtopic = df['subtopic'].apply(lambda x: pilihan_subtopic in x if isinstance(x, list) else pilihan_subtopic == x)
                
                df_filter = df[mask_tanggal & mask_subtopic]
                
                if df_filter.empty:
                    st.warning(f"Tidak ada berita untuk subtopik '{pilihan_subtopic}' pada rentang {tanggal_awal} hingga {tanggal_akhir}.")
                else:
                    st.success(f"Memproses analisis untuk {len(df_filter)} artikel...")
                    
                    # Eksekusi AI dan tampilkan hasilnya
                    teks_prompt = gabungkan_berita(df_filter)
                    hasil_analisis = panggil_gemini_api(teks_prompt, pilihan_subtopic)
                    
                    st.markdown(hasil_analisis)
                    tampilkan_artikel_pendukung(df_filter)