# Rumah A Predictor

Rumah A Predictor ialah aplikasi Streamlit untuk mengkaji corak nombor berdasarkan keputusan sejarah Toto 4D. Fokus projek ialah menjana dan mengecilkan ruang kajian secara telus—bukan menjamin keputusan masa hadapan.

## Aliran utama

1. Keputusan Top 3 terkini dibaca daripada `TotoHistoryAll.xlsx`.
2. **Bridge V1** menjana `base pair + 1 missing digit + 1 existing digit`.
3. **Bridge V2** menjana `base pair + 2 missing digit` atau `base pair + 2 existing digit`.
4. **2D Carry Engine** mengambil semua kombinasi dua digit daripada keputusan 2nd Prize dan menapis nombor Bridge yang mengandungi kombinasi tersebut.
5. **2D Carry Pilihan Kedudukan** mengaudit enam cara mengambil dua digit daripada 2nd Prize menggunakan 100 draw terdahulu, kemudian memaparkan penapis bagi satu kedudukan yang paling kerap dibawa.

Susunan digit tidak menentukan hit analisis. Nombor dengan digit penuh yang sama dianggap sepadan walaupun susunannya berbeza.

## Engine aktif

- Bridge V1
- Bridge V2
- 2D Carry Engine
- 2D Carry Pilihan Kedudukan
- Selection Engine eksperimen
- Bridge Pair Shortlist
- Bridge Dua Pair
- Carta 3D V2
- Backtest Bridge V1 + V2
- History Manager

Setiap engine kekal berasingan. Carta, family, pair ranking atau Selection Engine tidak boleh mempengaruhi 2D Carry tanpa audit khusus.

## Dapatan audit 2D Carry

Dalam audit walk-forward 100 draw:

- sekurang-kurangnya dua digit daripada 2nd Prize dibawa ke Top 3 berikutnya dalam `70/100` draw;
- nombor penuh yang membawa dua digit itu turut tersedia dalam Bridge V1 atau V2 dalam `61/100` draw;
- apabila fenomena carry berlaku, liputan Bridge ialah `61/70` atau `87.1%`.

Enam kedudukan yang diuji ialah `1+2`, `1+3`, `1+4`, `2+3`, `2+4` dan `3+4`. Kedudukan dipilih berdasarkan kekerapan sejarah sahaja. Nombor yang melepasi penapis tidak diberi skor atau ranking.

## Data

- `TotoHistoryAll.xlsx` — sumber aktif Top 3 dan History Manager.
- `TotoFullResult.xlsx` — sumber audit tambahan Special/Consolation; tidak dibaca dalam aliran Generate utama.

Streamlit boleh menyimpan kemas kini history ke GitHub melalui token dengan kebenaran `Contents: Read and write`.

## Prinsip pembangunan

- Bridge ialah sumber calon utama.
- Audit mesti walk-forward dan bebas data masa hadapan.
- Jangan mencipta rule, skor atau ranking tanpa arahan dan ujian yang jelas.
- Engine baharu dibina sebagai aliran berasingan.
- UI mesti ringkas, pantas dan sesuai digunakan pada telefon.
- Kegagalan audit direkodkan dengan jujur.

Rujukan teknikal dan keputusan projek yang lebih lengkap tersedia dalam `Rumah_A_Predictor_MASTER_CONTEXT.md`.
