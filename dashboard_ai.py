import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import google.generativeai as genai
from datetime import datetime, timedelta
import plotly.express as px

# IMPORT MODUL AI SUMMARY YANG BARU DIBUAT
from fitur_ai_summary import render_fitur_ai_summary

# Mengambil API Key dari brankas rahasia Streamlit
api_key = st.secrets.get("GEMINI_API_KEY")

st.set_page_config(page_title="AI & Data Intelligence", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# --- CSS INJECTION UNTUK TOMBOL PAGINASI & KARTU BERITA ---
st.markdown("""
<style>
/* Menghilangkan padding berlebih pada tombol paginasi */
div[data-testid="column"] button {
    margin-top: 5px;
    margin-bottom: 5px;
}
/* Memastikan caption paginasi berada di tengah */
.pagination-caption {
    text-align: center;
    color: #888;
    font-size: 14px;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data():
    DATABASE_URL = "postgresql+psycopg2://postgres:alfin1406@localhost:5432/pln_intelligence_db"
    engine = create_engine(DATABASE_URL)
    try:
        query = "SELECT * FROM tabel_berita_ai ORDER BY tanggal DESC"
        df = pd.read_sql(query, con=engine)
        if not df.empty:
            df['tanggal'] = pd.to_datetime(df['tanggal'])
            return df
    except Exception as e:
        st.error(f"⚠️ Gagal terhubung ke Database PostgreSQL. Error: {e}")
    return pd.DataFrame()

df = load_data()

@st.cache_data(show_spinner=False)
def generate_ai_summary(dataframe):
    if not api_key:
        return "⚠️ API Key Gemini belum diatur di secrets.toml."
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3.5-flash-lite')
    
    teks_berita = "".join([f"- {row['judul']}: {str(row.get('ringkasan_ai', ''))}\n" for index, row in dataframe.head(15).iterrows()])
        
    prompt = f"""
    Kamu adalah seorang Analis Bisnis Senior di PLN Icon Plus. 
    Tugasmu adalah menganalisis kumpulan ringkasan berita teknologi dari 2 minggu terakhir berikut ini dan membuat 'Laporan Eksekutif' singkat.
    Fokuslah pada tren kecerdasan buatan (AI) dan Infrastruktur Data (seperti Data Center, Cloud).
    
    Berita terbaru (14 Hari Terakhir):
    {teks_berita}
    
    Buatlah ringkasan dalam format Markdown dengan 2 poin utama:
    1. Tren AI & Data Terkini (2 kalimat)
    2. 2 Rekomendasi Peluang Bisnis untuk PLN Icon Plus berdasarkan tren tersebut (gunakan bullet points).
    Gunakan bahasa Indonesia yang profesional dan lugas.
    """
    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Gagal menghasilkan laporan eksekutif. Error: {e}"

@st.dialog("✨ Laporan Eksekutif AI (Tren 14 Hari Terakhir)")
def popup_laporan_ai(dataframe):
    st.info(f"🤖 Menganalisis {len(dataframe)} berita terhangat. Mohon tunggu beberapa detik...")
    st.write(generate_ai_summary(dataframe))

# ==========================================
# LOGIKA DASHBOARD UTAMA
# ==========================================
if not df.empty:
    def parse_topik(x):
        if isinstance(x, list): return x
        if isinstance(x, str):
            x = x.strip('{}[]').replace('"', '').replace("'", "")
            return [i.strip() for i in x.split(',')] if x else []
        return []
        
    df['teknologi_dibahas_list'] = df['teknologi_dibahas'].apply(parse_topik)
    semua_topik_unik = sorted(list(set(x for l in df['teknologi_dibahas_list'] for x in l)))
    lisensi_unik = [l for l in df['kategori_lisensi'].dropna().unique() if l.strip() != '']

    # ==========================================
    # SIDEBAR KONTROL
    # ==========================================
    with st.sidebar:
        st.title("⚙️ Panel Kontrol")
        st.markdown("Biarkan kosong untuk menampilkan **Semua Data**.")
        
        st.markdown("**1. Filter Global (Grafik & Metrik)**")
        pilihan_sumber = st.multiselect("🏢 Sumber Berita", options=df['sumber'].unique(), default=[], placeholder="Pilih sumber...")
        pilihan_topik = st.multiselect("🏷️ Topik / Subtopic", options=semua_topik_unik, default=[], placeholder="Pilih topik...")
        
        st.markdown("---")
        st.markdown("**2. Filter Arsip (Khusus Berita Bawah)**")
        lisensi_pilihan = st.multiselect("📜 Kategori Lisensi", options=lisensi_unik, default=[], placeholder="Pilih lisensi...")
        
        st.markdown("---")
        st.caption("PLN Icon Plus - AI Intelligence 2026")

    # ==========================================
    # KONTEN UTAMA
    # ==========================================
    st.title("📊 Dashboard Intelijen Bisnis: AI & Data")
    
    # IMPLEMENTASI ARAHAN MENTOR: Membaca kolom waktu_scrape dari Database
    if 'waktu_scrape' in df.columns and not df['waktu_scrape'].isna().all():
        # Ambil waktu paling terbaru dari pipeline
        waktu_run = pd.to_datetime(df['waktu_scrape'].max())
        tanggal_terakhir = waktu_run.strftime('%d %B %Y, %H:%M WIB')
    else:
        # Fallback jika data waktu_scrape kosong
        tanggal_terakhir = df['tanggal'].max().strftime('%d %B %Y')
        
    st.caption(f"🗓️ **Periode Pengambilan Data Terakhir:** {tanggal_terakhir}")
    
    st.markdown("Platform pemantauan tren teknologi otonom untuk mendukung strategi inovasi PLN Icon Plus.")
    st.divider()
    
    # --- APLIKASI FILTER LOGIKA "KOSONG = SEMUA" ---
    df_global = df[df['sumber'].isin(pilihan_sumber)] if pilihan_sumber else df.copy()
    
    if pilihan_topik:
        df_global = df_global[df_global['teknologi_dibahas_list'].apply(lambda x: any(item in pilihan_topik for item in x))]
    
    if df_global.empty:
        st.warning("Data kosong berdasarkan filter di Sidebar. Silakan sesuaikan pilihan Anda.")
    else:
        # === METRIK ===
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total Berita", f"{len(df_global)} Artikel Terkumpul")
        col_m2.metric("Sumber Aktif", f"{df_global['sumber'].nunique()} Portal Berita")
        col_m3.metric("Fokus Data", "AI & Infrastruktur")
        
        st.markdown("<br>", unsafe_allow_html=True) 
        
        # === TOMBOL AI GLOBAL ===
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2: 
            if st.button("🤖 Generate Laporan Eksekutif AI (14 Hari Terakhir)", use_container_width=True, type="primary"):
                batas_14_hari = pd.Timestamp.now().normalize() - pd.Timedelta(days=14)
                df_2_minggu = df_global[df_global['tanggal'] >= batas_14_hari]
                if df_2_minggu.empty: st.warning("Tidak ada data dalam 14 hari terakhir.")
                else: popup_laporan_ai(df_2_minggu)
        
        st.markdown("---")
        
        # === GRAFIK ===
        col_trend, col_dist = st.columns([1.5, 1])
        
        with col_trend:
            st.subheader("📈 Tren Publikasi")
            df_chart = df_global.copy()
            df_chart['Minggu'] = df_chart['tanggal'].dt.to_period('W').apply(lambda r: r.start_time)
            tren_mingguan = df_chart.groupby('Minggu').size().reset_index(name='Jumlah Artikel')
            
            fig_line = px.line(tren_mingguan, x='Minggu', y='Jumlah Artikel', markers=True, height=350)
            fig_line.update_layout(
                xaxis=dict(title="", tickformat="%d %b %Y", showgrid=False), 
                yaxis=dict(title="Jumlah Artikel", fixedrange=True), 
                margin=dict(l=0, r=0, t=10, b=0), 
                hovermode="x unified"
            )
            st.plotly_chart(fig_line, use_container_width=True)

        with col_dist:
            st.subheader("📊 Distribusi Subtopic")
            
            df_exploded = df_global.explode('teknologi_dibahas_list')
            if pilihan_topik:
                df_exploded = df_exploded[df_exploded['teknologi_dibahas_list'].isin(pilihan_topik)]
                
            topik_count = df_exploded['teknologi_dibahas_list'].value_counts().reset_index()
            topik_count.columns = ['Subtopic', 'Jumlah']
            
            fig_bar = px.bar(topik_count, x='Jumlah', y='Subtopic', orientation='h', text='Jumlah', color_discrete_sequence=['#3b82f6'], height=350)
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="", yaxis_title="", margin=dict(l=0, r=0, t=10, b=0))
            
            st.plotly_chart(fig_bar, use_container_width=True)
            st.caption("*Catatan: Satu artikel dapat memiliki lebih dari satu subtopik (Multi-label).*")

        # ==========================================
        # PEMANGGILAN KOMPONEN BARU: AI SUMMARY PER SUBTOPIC
        # ==========================================
        # Menyiapkan kolom 'subtopic' karena modul `fitur_ai_summary.py` mengincar nama tersebut
        df_untuk_ai = df_global.copy()
        if 'teknologi_dibahas_list' in df_untuk_ai.columns:
            df_untuk_ai['subtopic'] = df_untuk_ai['teknologi_dibahas_list']
            
        render_fitur_ai_summary(df_untuk_ai, semua_topik_unik)
        
        st.markdown("---")

        # === ARSIP BERITA (GRID 3 KOLOM & PAGINASI LENGKAP) ===
        st.subheader("📰 Arsip Berita Publikasi")
        
        df_filtered_archive = df_global[df_global['kategori_lisensi'].isin(lisensi_pilihan)] if lisensi_pilihan else df_global.copy()

        # Konfigurasi Paginasi: 21 Artikel per halaman (7 baris x 3 kolom)
        ITEM_PER_HALAMAN = 21  
        total_item = len(df_filtered_archive)
        
        if total_item > 0:
            total_halaman = max(1, (total_item - 1) // ITEM_PER_HALAMAN + 1)
            
            if 'halaman_saat_ini' not in st.session_state:
                st.session_state.halaman_saat_ini = 1
                
            def ganti_halaman(nomor):
                st.session_state.halaman_saat_ini = nomor
                
            if st.session_state.halaman_saat_ini > total_halaman:
                st.session_state.halaman_saat_ini = 1

            idx_awal = (st.session_state.halaman_saat_ini - 1) * ITEM_PER_HALAMAN
            idx_akhir = idx_awal + ITEM_PER_HALAMAN
            df_halaman_ini = df_filtered_archive.iloc[idx_awal:idx_akhir]

            st.markdown(f"<p class='pagination-caption'>Menampilkan {idx_awal + 1}–{min(idx_akhir, total_item)} dari total {total_item} artikel</p>", unsafe_allow_html=True)

            # --- RENDER GRID 3 KOLOM ---
            # Pecah data menjadi kelompok per-3 artikel
            baris_berita = [df_halaman_ini.iloc[i:i+3] for i in range(0, len(df_halaman_ini), 3)]

            for baris in baris_berita:
                kolom = st.columns(3) # Buat 3 kolom Streamlit
                
                for idx, (_, row) in enumerate(baris.iterrows()):
                    with kolom[idx]:
                        with st.container(border=True): # Buat bentuk kartu dengan border
                            
                            # 1. Gambar
                            if 'gambar' in row and pd.notna(row['gambar']) and str(row['gambar']).startswith('http'):
                                st.image(str(row['gambar']), use_container_width=True)
                            else:
                                st.image("https://via.placeholder.com/400x250?text=No+Image", use_container_width=True)
                                
                            # 2. Judul & Meta
                            st.markdown(f"**{row['judul']}**")
                            tgl_format = row['tanggal'].strftime('%d %b %Y') if pd.notna(row['tanggal']) else '-'
                            sumber = row.get('sumber', 'Portal')
                            lisensi = row.get('kategori_lisensi', '-')
                            st.caption(f"📅 {tgl_format} | 🏢 **{sumber}** | 📜 {lisensi}")
                            
                            # 3. Ringkasan (Truncated)
                            ringkasan = str(row.get('ringkasan_ai', ''))
                            if len(ringkasan) > 130: ringkasan = ringkasan[:127] + "..."
                            st.write(f"<span style='font-size: 13px;'>{ringkasan}</span>", unsafe_allow_html=True)
                            
                            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                            
                            # 4. Tags Subtopic
                            topik_rapi = ", ".join(row['teknologi_dibahas_list']) if len(row['teknologi_dibahas_list']) > 0 else "-"
                            st.markdown(f"<span style='font-size: 11px; color: #888;'>🏷️ {topik_rapi}</span>", unsafe_allow_html=True)
                            
                            # 5. Link Asli
                            st.markdown(f"<br><a href='{row['link']}' style='color:#3b82f6; text-decoration:none; font-weight:bold;'>🔗 Baca Artikel Asli ➔</a>", unsafe_allow_html=True)

            # --- RENDER TOMBOL NAVIGASI PAGINASI ---
            st.markdown("<br>", unsafe_allow_html=True)
            # Area tengah dilebarkan agar muat untuk tombol First/Last
            col_nav_kiri, col_nav_tengah, col_nav_kanan = st.columns([1, 4, 1]) 
            
            with col_nav_tengah:
                hal_skrg = st.session_state.halaman_saat_ini
                
                start_hal = max(1, hal_skrg - 2)
                end_hal = min(total_halaman, start_hal + 4)
                start_hal = max(1, end_hal - 4)
                
                deret_halaman = range(start_hal, end_hal + 1)
                jml_tombol = len(deret_halaman) + 4 # (First, Prev, [Numbers], Next, Last)
                
                baris_tombol = st.columns(jml_tombol)
                
                # Tombol First (Awal)
                with baris_tombol[0]:
                    st.button("« Awal", disabled=(hal_skrg == 1), on_click=ganti_halaman, args=(1,), use_container_width=True)
                    
                # Tombol Prev (Sebelumnya)
                with baris_tombol[1]:
                    st.button("❮", disabled=(hal_skrg == 1), on_click=ganti_halaman, args=(hal_skrg - 1,), use_container_width=True)
                
                # Tombol Angka Halaman
                for i, no_hal in enumerate(deret_halaman):
                    with baris_tombol[i + 2]:
                        tipe = "primary" if no_hal == hal_skrg else "secondary"
                        st.button(str(no_hal), on_click=ganti_halaman, args=(no_hal,), type=tipe, use_container_width=True)
                
                # Tombol Next (Berikutnya)
                with baris_tombol[-2]:
                    st.button("❯", disabled=(hal_skrg == total_halaman), on_click=ganti_halaman, args=(hal_skrg + 1,), use_container_width=True)
                    
                # Tombol Last (Akhir)
                with baris_tombol[-1]:
                    st.button("Akhir »", disabled=(hal_skrg == total_halaman), on_click=ganti_halaman, args=(total_halaman,), use_container_width=True)

        else:
            st.info("Tidak ada berita yang sesuai dengan filter saat ini.")

else:
    st.error("Belum ada data di PostgreSQL. Pastikan skrip load_to_db.py sudah dijalankan.")