FROM apache/airflow:2.10.2

# Memasang library yang dibutuhkan oleh pipeline PLN Icon Plus, termasuk Gemini AI
RUN pip install --no-cache-dir pandas sqlalchemy psycopg2-binary requests beautifulsoup4 google-generativeai