import pandas as pd
from sqlalchemy import create_engine, text

# Konek ke Database
DATABASE_URL = "postgresql+psycopg2://postgres:alfin1406@localhost:5432/pln_intelligence_db"
engine = create_engine(DATABASE_URL)

# Kamus Baru (Sesuai AI & Data Infrastruktur)
KAMUS_TOPIK = {
    "Technology": ["ai", "artificial intelligence", "kecerdasan buatan", "machine learning", "algoritma", "model bahasa", "llm", "neural network", "deep learning"],
    "Infrastructure": ["data center", "pusat data", "cloud", "server", "gpu", "nvidia", "komputasi", "jaringan", "infrastruktur", "compute", "chips", "semiconductor"],
    "Energy": ["air", "listrik", "pln", "energi", "karbon", "pembangkit", "jatiluhur", "ramah lingkungan", "emisi", "energy", "power", "nuclear", "grid", "emission"],
    "Investment": ["investasi", "triliun", "miliar", "dana", "saham", "startup", "akuisisi", "proyek", "investor", "ekonomi", "investment", "funding", "billion", "million", "acquisition", "valuation"],
    "Generative AI & LLM": ["llm", "large language model", "genai", "generative ai", "chatgpt", "gemini", "claude", "llama", "hugging face", "mistral", "prompt"],
    "AI Hardware & Chips": ["gpu", "nvidia", "amd", "tpu", "chip", "semiconductor", "tensor", "silicon", "perangkat keras ai"],
    "Data Center & Cloud": ["data center", "pusat data", "aws", "azure", "google cloud", "cloud computing", "komputasi awan", "server", "hosting"],
    "AI Regulation & Ethics": ["regulasi", "undang-undang", "etika", "bias ai", "hak cipta", "legalitas", "kebijakan", "keamanan data", "privasi", "reputasi"],
    "Cyber Security in AI": ["ransomware", "hacker", "peretas", "malware", "phishing", "kebocoran data", "serangan siber", "cyber threat"]
}

def get_topik(isi_teks):
    if not isi_teks: return []
    teks_lower = str(isi_teks).lower()
    return [topik for topik, kata_kunci in KAMUS_TOPIK.items() if any(k in teks_lower for k in kata_kunci)]

def main():
    print("🔄 Menarik data historis dari PostgreSQL...")
    df = pd.read_sql("SELECT link, isi_berita FROM tabel_berita_ai", con=engine)
    
    print(f"📊 Menemukan {len(df)} artikel. Mulai melabeli ulang subtopic...")
    
    with engine.begin() as connection:
        berita_terupdate = 0
        for index, row in df.iterrows():
            topik_baru = get_topik(row['isi_berita'])
            
            # Format ke literal array PostgreSQL '{a,b,c}'
            array_str = "{" + ",".join([f'"{t}"' for t in topik_baru]) + "}" if topik_baru else "{}"
            
            # Update database
            query = text("UPDATE tabel_berita_ai SET teknologi_dibahas = CAST(:topik AS text[]) WHERE link = :link")
            connection.execute(query, {"topik": array_str, "link": row['link']})
            berita_terupdate += 1
            
    print(f"✅ Selesai! Berhasil memperbarui {berita_terupdate} artikel historis di database dengan subtopic baru.")

if __name__ == "__main__":
    main()