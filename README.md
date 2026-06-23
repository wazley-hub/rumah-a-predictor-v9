# Rumah A Predictor V14

V14 features:
- V14A: Padam rekod
- V14B: Cari Draw No
- V14C: Download Current App History dan Latest GitHub History
- V14D: Statistik ringkas dataset
- History Manager lengkap
- Tambah/update keputusan
- Auto-save `TotoHistoryAll.xlsx` terus ke GitHub menggunakan Streamlit Secrets
- Generate ramalan berdasarkan history terkini

Required Streamlit secret:
GITHUB_TOKEN = "your_github_token_here"

Upload/replace ke GitHub:
- app.py
- README.md

`requirements.txt` tidak wajib jika tiada perubahan.
Jangan replace `TotoHistoryAll.xlsx` supaya history semasa kekal.
