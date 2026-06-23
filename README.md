# Rumah A Predictor V12

V12 features:
- Tambah keputusan baru
- Update keputusan sedia ada jika Draw No sudah wujud
- Auto-save `TotoHistoryAll.xlsx` terus ke GitHub menggunakan Streamlit Secrets
- Generate ramalan berdasarkan history terkini

Required Streamlit secret:
GITHUB_TOKEN = "your_github_token_here"

Cara update:
Upload/replace fail berikut ke GitHub repo:
- app.py
- requirements.txt
- README.md

Jangan replace `TotoHistoryAll.xlsx` jika mahu kekalkan history semasa dalam GitHub.
