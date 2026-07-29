# Rumah A Predictor

> Aplikasi analisis nombor berasaskan sejarah keputusan, struktur pasangan digit dan pengesahan corak.

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Status](https://img.shields.io/badge/Status-Active-159957)](#status-projek)

## Gambaran keseluruhan

Rumah A Predictor ialah ruang kerja analisis untuk mengkaji bagaimana digit dan pasangan digit daripada keputusan Top 3 terdahulu membentuk kumpulan nombor bagi draw seterusnya.

Fokus projek ini bukan mendakwa boleh meramal masa depan. Tujuannya ialah:

- mengaudit kesilapan dan kejayaan lalu;
- mengenal pasti struktur pasangan digit yang berulang;
- menghasilkan ruang nombor secara konsisten melalui Bridge;
- mengecilkan ruang tersebut melalui signal yang diuji secara berasingan; dan
- menyimpan keputusan serta bukti backtest untuk kajian seterusnya.

## Enjin semasa

| Komponen | Fungsi |
|---|---|
| **Bridge V1** | Menggabungkan base pair dengan satu digit missing dan satu digit existing. |
| **Bridge V2** | Mengembangkan base pair menggunakan dua digit missing atau dua digit existing. |
| **Selection Engine** | Menyenaraikan 10 pilihan daripada ruang Bridge menggunakan audit Pair Slot dalam tempoh 100 draw terkini. |
| **Bridge Pair Shortlist** | Membuka pilihan Bridge mengikut pair semasa supaya setiap pair boleh diperiksa dan disalin secara berasingan. |
| **Bridge Dua Pair** | Menunjukkan nombor yang mengekalkan generator pair serta mempunyai sokongan pair kedua. |
| **Carta 3D V2** | Rujukan visual Menegak dan L untuk pemerhatian 3D; kekal berasingan daripada Selection Engine. |
| **Backtest Bridge V1 + V2** | Mengukur liputan sejarah Bridge dengan paparan ringkas dan fail audit terperinci. |

## Aliran analisis

```text
Keputusan Top 3 terkini
        │
        ├── Base pair unik
        │       ├── Bridge V1
        │       └── Bridge V2
        │
        ├── Selection Engine (100 draw)
        ├── Bridge Pair Shortlist
        ├── Bridge Dua Pair
        └── Carta 3D V2 (rujukan berasingan)
```

Setiap laluan mempunyai tujuan tersendiri. Carta, pair shortlist dan Selection Engine tidak digabungkan secara automatik supaya satu pemerhatian tidak mengubah keputusan laluan lain.

## Pengurusan data

| Fail | Kegunaan |
|---|---|
| `TotoHistoryAll.xlsx` | Sejarah Draw No, tarikh dan keputusan Top 3. |
| `TotoFullResult.xlsx` | Keputusan penuh termasuk Special dan Consolation untuk audit tambahan. |

History Manager membolehkan pengguna:

- menambah atau mengemas kini keputusan;
- mencari draw tertentu;
- membetulkan rekod tersilap;
- memadam rekod yang tidak diperlukan; dan
- menyimpan perubahan ke repositori GitHub apabila auto-save diaktifkan.

## Menjalankan secara tempatan

```bash
pip install -r requirements.txt
streamlit run app.py
```

Selepas app dibuka:

1. Semak keputusan terkini.
2. Masukkan tiga keputusan Top 3.
3. Tekan **Generate**.
4. Nilai output setiap enjin secara berasingan.
5. Gunakan Backtest untuk mengesahkan pemerhatian terhadap sejarah.

## Struktur repositori

```text
.
├── app.py
├── requirements.txt
├── TotoHistoryAll.xlsx
├── TotoFullResult.xlsx
├── README.md
├── CHANGELOG.md
├── Rumah_A_Predictor_MASTER_CONTEXT.md
└── docs/
    ├── DEPLOY_README.txt
    └── archive/
        └── CHANGELOG_V31_*.txt
```

## Prinsip pembangunan

- **Bridge-first** — Bridge V1 dan V2 ialah generator utama.
- **Signal berasingan** — signal baharu diuji di luar aliran utama sebelum dipertimbangkan.
- **Walk-forward** — penilaian menggunakan maklumat yang tersedia sebelum sesuatu draw.
- **Tiada data leakage** — keputusan masa hadapan tidak digunakan untuk membina pilihan draw terdahulu.
- **Ringkas dahulu** — engine baharu mesti memberi nilai tambah yang jelas sebelum dimasukkan ke app.
- **Boleh diaudit** — output penting mesti mempunyai sumber dan laluan yang boleh diperiksa.

## Status projek

Projek sedang dibangunkan secara aktif. Seni bina semasa telah dipermudah kepada Bridge V1, Bridge V2 dan alat sokongan yang boleh diaudit. Engine keluarga, AI Pick dan ranking legasi tidak lagi menjadi sebahagian daripada aliran aktif.

## Nota penggunaan

Rumah A Predictor ialah alat analisis eksperimen. Output menunjukkan kemungkinan berdasarkan formula dan sejarah; ia bukan jaminan keputusan atau nasihat kewangan. Sebarang tindakan berdasarkan output adalah tanggungjawab pengguna sendiri.
