import json

def main():
    print("Membangun Pipeline Data: Tahap 2 (AI Summarization Preparation)")
    print("Membaca file insight_ai_cnbc.json...")
    
    try:
        with open('insight_ai_cnbc.json', 'r', encoding='utf-8') as f:
            berita_list = json.load(f)
            
        if not berita_list:
            print("File JSON kosong.")
            return

        print(f"Berhasil memuat {len(berita_list)} berita.\n")
        
        # Menyusun daftar judul untuk dikirim ke AI
        kumpulan_judul = ""
        for i, b in enumerate(berita_list, 1):
            kumpulan_judul += f"{i}. {b['judul']}\n"

        # Merancang Prompt Sistem (Perintah Khusus untuk AI)
        prompt = f"""
Sebagai seorang Business Intelligence Analyst di PLN Icon Plus (perusahaan penyedia internet, data center, dan infrastruktur IT), tugasmu adalah menganalisis kumpulan berita teknologi terbaru berikut ini:

{kumpulan_judul}
Instruksi:
1. Buatlah 1 paragraf ringkasan eksekutif tentang tren AI saat ini berdasarkan berita di atas.
2. Identifikasi ancaman/masalah utama yang sedang dihadapi industri terkait AI.
3. Berikan 2 rekomendasi peluang bisnis/layanan (Business Insight) yang bisa ditawarkan oleh PLN Icon Plus untuk memecahkan masalah tersebut.
"""
        
        # Menyimpan prompt ke file teks agar mudah disalin
        with open('prompt_siap_pakai.txt', 'w', encoding='utf-8') as f:
            f.write(prompt)
            
        print("=" * 70)
        print("✅ Super Prompt berhasil dibuat dan disimpan di 'prompt_siap_pakai.txt'!")
        print("Silakan buka file teks tersebut, salin isinya, dan tempelkan ke ChatGPT atau Gemini untuk melihat hasil analisisnya.")

    except FileNotFoundError:
        print("Error: File insight_ai_cnbc.json tidak ditemukan. Pastikan file tersebut ada di folder yang sama.")

if __name__ == "__main__":
    main()