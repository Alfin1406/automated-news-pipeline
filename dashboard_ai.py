import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import google.generativeai as genai
from datetime import datetime, timedelta
import plotly.express as px  # <-- Library baru untuk grafik pro

# Mengambil API Key dari brankas rahasia Streamlit
api_key = st.secrets.get("GEMINI_API_KEY")

st.set_page_config(page_title="AI & Data Intelligence", page_icon="📊", layout="wide")

# === JUDUL & GLOBAL FILTER DI POJOK KANAN ATAS ===
col_judul, col_filter_global = st.columns([3, 1])

with col_judul:
    st.title("📊 Dashboard Intelijen Bisnis: AI & Data Infrastruktur")
    st.markdown("Platform pemantauan tren teknologi otonom untuk mendukung strategi inovasi dan penjualan PLN Icon Plus.")

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
    
    teks_berita = ""
    for index, row in dataframe.head(15).iterrows():
        teks_berita += f"- {row['judul']}: {str(row.get('ringkasan_ai', ''))}\n"
        
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
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gagal menghasilkan laporan eksekutif. Error: {e}"

@st.dialog("✨ Laporan Eksekutif AI (Tren 14 Hari Terakhir)")
def popup_laporan_ai(dataframe):
    st.info(f"🤖 Menganalisis {len(dataframe)} berita terhangat. Mohon tunggu beberapa detik...")
    hasil_ai = generate_ai_summary(dataframe)
    st.success("Analisis selesai!")
    st.write(hasil_ai)

# --- LOGIKA DASHBOARD UTAMA ---
if not df.empty:
    with col_filter_global:
        st.write("") 
        pilihan_sumber = st.multiselect(
            "🏢 Filter Sumber Berita:", 
            options=df['sumber'].unique(), 
            default=df['sumber'].unique()
        )
        
    st.divider()

    df_global = df[df['sumber'].isin(pilihan_sumber)]
    
    if df_global.empty:
        st.warning("Pilih setidaknya satu sumber berita untuk menampilkan data dashboard.")
    else:
        # === METRIK ATAS ===
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Berita (Terfilter)", f"{len(df_global)} Artikel")
        col2.metric("Sumber Data Aktif", df_global['sumber'].nunique())
        col3.metric("Fokus Sektor", "AI & Data Infrastruktur")
        
        # === FITUR BARU: LINE CHART PLOTLY (TERKUNCI & BERDASARKAN MINGGU) ===
        st.markdown("---")
        st.subheader("📈 Tren Publikasi Berita AI")
        st.caption("Jumlah pemberitaan AI & Data Infrastruktur berdasarkan Minggu")
        
        df_chart = df_global.copy()
        
        # 1. Mengelompokkan data per 1 Minggu ('W'). (Ganti 'W' menjadi '2W' jika mentor ngotot ingin 14 hari)
        df_chart['Minggu'] = df_chart['tanggal'].dt.to_period('2W').apply(lambda r: r.start_time)
        tren_mingguan = df_chart.groupby('Minggu').size().reset_index(name='Jumlah Artikel')
        
        # 2. Mengubah tanggal menjadi string (Kategori) agar sumbu X terkunci persis seperti kategori berita
        tren_mingguan['Minggu'] = tren_mingguan['Minggu'].dt.strftime('%Y-%m-%d')
        
        # 3. Menggambar grafik menggunakan Plotly (Lebih pro dan ada titiknya)
        fig = px.line(
            tren_mingguan, 
            x='Minggu', 
            y='Jumlah Artikel',
            markers=True # Memunculkan titik-titik di garis
        )
        
        # 4. Mematikan fitur Zoom dan Pan agar sumbu X tetap (STAY) tidak bergeser
        fig.update_layout(
            xaxis=dict(fixedrange=True, type='category'), # type='category' memaksa tulisan tanggal diam di tempat
            yaxis=dict(fixedrange=True),
            margin=dict(l=0, r=0, t=10, b=0),
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")

        col_exec, col_trend = st.columns([1.5, 1])
        
        with col_exec:
            st.subheader("💡 Laporan Eksekutif Bisnis")
            st.markdown("Klik tombol di bawah ini untuk meminta AI menganalisis tren 2 minggu terakhir secara *on-demand*.")
            
            if st.button("🤖 Generate Laporan Bisnis AI", use_container_width=True):
                batas_14_hari = pd.Timestamp.now().normalize() - pd.Timedelta(days=14)
                df_2_minggu = df_global[df_global['tanggal'] >= batas_14_hari]
                
                if df_2_minggu.empty:
                    st.warning("Tidak ada data berita relevan dalam 14 hari terakhir.")
                else:
                    popup_laporan_ai(df_2_minggu)
                
        with col_trend:
            st.subheader("🎯 Distribusi Lisensi AI")
            st.markdown("Perbandingan jumlah artikel berdasarkan kategori lisensi:")
            
            lisensi_count = df_global['kategori_lisensi'].value_counts().reset_index()
            lisensi_count.columns = ['Kategori Lisensi', 'Jumlah Artikel']
            st.dataframe(lisensi_count, hide_index=True, use_container_width=True)
                
        st.divider()

        # === ARSIP BERITA TERKINI ===
        st.subheader("📰 Arsip Berita Terkini")
        
        lisensi_unik = [l for l in df_global['kategori_lisensi'].dropna().unique() if l.strip() != '']
        lisensi_pilihan = st.multiselect("Filter Lisensi AI Spesifik:", options=lisensi_unik, default=lisensi_unik)
        
        df_filtered_archive = df_global[df_global['kategori_lisensi'].isin(lisensi_pilihan)]

        for index, row in df_filtered_archive.iterrows():
            with st.container():
                col_img, col_txt = st.columns([1, 4])
                
                with col_img:
                    if 'gambar' in row and pd.notna(row['gambar']) and str(row['gambar']).startswith('http'):
                        st.image(str(row['gambar']), use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/400x250?text=Tidak+Ada+Gambar", use_container_width=True)
                        
                with col_txt:
                    st.subheader(row['judul'])
                    tgl_format = row['tanggal'].strftime('%Y-%m-%d') if pd.notna(row['tanggal']) else 'Tidak diketahui'
                    st.caption(f"📅 {tgl_format} | 🏢 Sumber: **{row.get('sumber', 'Portal Berita')}**")
                    st.write(str(row.get('ringkasan_ai', 'Rangkuman tidak tersedia.')))
                    
                    topik_mentah = row.get('teknologi_dibahas', [])
                    if isinstance(topik_mentah, (list, tuple)) or type(topik_mentah).__name__ == 'ndarray':
                        topik_rapi = ", ".join(topik_mentah) if len(topik_mentah) > 0 else "-"
                    else:
                        topik_rapi = str(topik_mentah)
                    
                    st.markdown(f"**🏷️ Topik/Teknologi:** `{topik_rapi}`  |  **📜 Lisensi:** `{row.get('kategori_lisensi', '-')}`")
                    st.markdown(f"[🔗 Baca Artikel Asli di Sini]({row['link']})")
                    
            st.markdown("---")

else:
    st.error("Belum ada data di PostgreSQL. Pastikan skrip load_to_db.py sudah dijalankan.")