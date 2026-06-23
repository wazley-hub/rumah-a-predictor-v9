# Rumah A Predictor V13

V13 features:
- History Manager
- Papar 10 draw terakhir dalam app
- Pilih Draw No untuk edit/update terus
- Tambah keputusan baru seperti biasa
- Auto-save `TotoHistoryAll.xlsx` terus ke GitHub menggunakan Streamlit Secrets
- Generate ramalan berdasarkan history terkini

Required Streamlit secret:
GITHUB_TOKEN = "your_github_token_here"

Upload/replace ke GitHub:
- app.py
- README.md

`requirements.txt` tidak wajib jika tiada perubahan.
Jangan replace `TotoHistoryAll.xlsx` supaya history semasa kekal.
