# Rumah A Predictor V11

V11 features:
- Tambah keputusan baru dalam app
- Auto-save `TotoHistoryAll.xlsx` terus ke GitHub menggunakan Streamlit Secrets
- Generate ramalan berdasarkan history terkini
- Download Excel backup

Required Streamlit secret:

```toml
GITHUB_TOKEN = "your_github_token_here"
```

Jangan letak token dalam `app.py`.
