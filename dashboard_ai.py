import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import google.generativeai as genai
from datetime import datetime, timedelta
import plotly.express as px

# Mengambil API Key dari brankas rahasia Streamlit
api_key = st.secrets.get("GEMINI_API_KEY")

st.set_page_config(page_title="AI & Data Intelligence", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

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
    # SIDEBAR KONTROL (BERSIH & MINIMALIS)
    # ==========================================
    with st.sidebar:
        st.title("⚙️ Panel Kontrol")
        st.markdown("Biarkan kosong untuk menampilkan **Semua Data**.")
        
        st.markdown("**1. Filter Global (Grafik & Metrik)**")
        # Default diubah menjadi kosong []
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
    st.markdown("Platform pemantauan tren teknologi otonom untuk mendukung strategi inovasi PLN Icon Plus.")
    st.divider()
    
    # --- APLIKASI FILTER LOGIKA "KOSONG = SEMUA" ---
    # Jika pilihan_sumber kosong, pakai semua sumber. Jika ada isinya, filter sesuai isi.
    df_global = df[df['sumber'].isin(pilihan_sumber)] if pilihan_sumber else df.copy()
    
    # Jika pilihan_topik kosong, abaikan filter. Jika ada isinya, saring array-nya.
    if pilihan_topik:
        df_global = df_global[df_global['teknologi_dibahas_list'].apply(lambda x: any(item in pilihan_topik for item in x))]
    
    if df_global.empty:
        st.warning("Data kosong berdasarkan filter di Sidebar. Silakan sesuaikan pilihan Anda.")
    else:
        # === METRIK (LEBIH LUAS KARENA TOMBOL AI DIPINDAH) ===
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total Berita", f"{len(df_global)} Artikel Terkumpul")
        col_m2.metric("Sumber Aktif", f"{df_global['sumber'].nunique()} Portal Berita")
        col_m3.metric("Fokus Data", "AI & Infrastruktur")
        
        st.markdown("<br>", unsafe_allow_html=True) # Jarak estetik
        
        # === TOMBOL AI (Eksklusif di Tengah) ===
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2: # Menempatkan tombol persis di tengah agar elegan
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
            # Tetap dikelompokkan per 2 minggu
            df_chart['Minggu'] = df_chart['tanggal'].dt.to_period('W').apply(lambda r: r.start_time)
            tren_mingguan = df_chart.groupby('Minggu').size().reset_index(name='Jumlah Artikel')
            
            # MEMPERBAIKI SUMBU X: Biarkan format datetime agar Plotly pintar mengaturnya
            fig_line = px.line(tren_mingguan, x='Minggu', y='Jumlah Artikel', markers=True, height=350)
            fig_line.update_layout(
                xaxis=dict(
                    title="",
                    tickformat="%d %b %Y", # Format cantik: 15 Oct 2026
                    showgrid=False
                ), 
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

        st.markdown("---")

        # === ARSIP BERITA ===
        st.subheader("📰 Arsip Berita Publikasi")
        
        # Filter logika "Kosong = Semua" untuk lisensi
        df_filtered_archive = df_global[df_global['kategori_lisensi'].isin(lisensi_pilihan)] if lisensi_pilihan else df_global.copy()

        for index, row in df_filtered_archive.iterrows():
            with st.container():
                col_img, col_txt = st.columns([1, 5])
                with col_img:
                    if 'gambar' in row and pd.notna(row['gambar']) and str(row['gambar']).startswith('http'):
                        st.image(str(row['gambar']), use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/400x250?text=No+Image", use_container_width=True)
                        
                with col_txt:
                    st.markdown(f"**{row['judul']}**")
                    tgl_format = row['tanggal'].strftime('%d %b %Y') if pd.notna(row['tanggal']) else 'Tidak diketahui'
                    st.caption(f"📅 {tgl_format} | 🏢 **{row.get('sumber', 'Portal Berita')}** | 📜 {row.get('kategori_lisensi', '-')}")
                    
                    topik_rapi = ", ".join(row['teknologi_dibahas_list']) if len(row['teknologi_dibahas_list']) > 0 else "-"
                    st.write(f"<span style='font-size: 14px;'>{str(row.get('ringkasan_ai', ''))}</span>", unsafe_allow_html=True)
                    st.markdown(f"<span style='font-size: 12px; color: #888;'>🏷️ {topik_rapi} &nbsp;|&nbsp; <a href='{row['link']}' style='color:#3b82f6; text-decoration:none;'>🔗 Baca Artikel Asli</a></span>", unsafe_allow_html=True)
            st.divider()
else:
    st.error("Belum ada data di PostgreSQL. Pastikan skrip load_to_db.py sudah dijalankan.")