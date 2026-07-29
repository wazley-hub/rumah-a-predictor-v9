# Changelog

Perubahan penting Rumah A Predictor direkodkan di sini. Rekod pembangunan lama disimpan dalam `docs/archive/`.

## 30 Julai 2026

### 2D Carry Engine

- Menambah penapis berdasarkan semua kombinasi dua digit daripada keputusan 2nd Prize.
- Susunan dua digit diabaikan semasa semakan nombor penuh.
- Bridge V1 dan Bridge V2 dipaparkan secara berasingan.
- Nombor family yang sama tidak diulang.
- Menambah butang `Copy Semua 2D Carry` dan expander khusus.

### 2D Carry Pilihan Kedudukan

- Menambah blok kedua yang berasingan daripada 2D Carry asal.
- Mengaudit enam kedudukan: `1+2`, `1+3`, `1+4`, `2+3`, `2+4` dan `3+4`.
- Menggunakan 100 transisi terdahulu secara walk-forward.
- Memilih satu kedudukan berdasarkan kekerapan carry sejarah.
- Menapis Bridge V1 dan V2 menggunakan dua digit daripada kedudukan tersebut.
- Menambah butang `Copy Pilihan Kedudukan` dan expander khusus.
- Tiada skor atau ranking dibuat dalam kalangan nombor yang melepasi penapis.

### Audit

- Dua digit daripada 2nd Prize dibawa ke Top 3 berikutnya dalam `70/100` draw.
- Nombor penuh berkaitan turut tersedia dalam Bridge dalam `61/100` draw.
- Liputan Bridge bersyarat apabila carry berlaku: `61/70 (87.1%)`.
- Audit kes `4816 → 3628 / 2126` mengesahkan:
  - `86` dibawa sebagai `68` dalam `3628`;
  - `3628` tersedia dalam Bridge V1;
  - `16` dibawa dalam `2126`, tetapi nombor penuh itu tidak tersedia dalam Bridge.

### Dokumentasi

- README dikemas kini kepada aliran Bridge → 2D Carry.
- Master Context dikemas kini dengan definisi, audit dan larangan mencampurkan engine.
- Selection Engine dan ranking pair lama tidak dianggap sebahagian daripada formula 2D Carry.

## 29 Julai 2026

### Seni bina Bridge-first

- Bridge V1 dan V2 dikekalkan sebagai generator utama.
- Base pair songsang yang membawa digit sama dideduplikasi.
- Selection Engine menggunakan lookback 100 draw.
- Backtest menggunakan cache dan paparan `Quick Review`, `Summary` serta `Detail`.
- Carta 3D V2 dikekalkan sebagai rujukan berasingan.
- UI Generate, butang Copy dan expander dikemas semula.

### Dibuang atau dinyahaktifkan

- AI Pick, Strong Buy dan Backup Pool
- empat model utama lama
- Family Ranker V1/V2
- Combined dan Meta Ranker
- Core Family Consensus
- Fourth Digit Completion
- Conditional Route Selector
- DDE dalam backtest utama
- Signal Lab
- Result Chart Board V3.1
- Top 10 Lintas Bulan

Kod family dan ranking legasi tidak lagi menjadi asas engine baharu.

## Data dan infrastruktur

- `TotoHistoryAll.xlsx` ialah sumber aktif Top 3.
- `TotoFullResult.xlsx` disimpan untuk audit tambahan.
- History Manager menyokong simpanan ke GitHub.
- Streamlit Cloud membaca kod dan data daripada branch utama repositori.

Jika changelog arkib bercanggah dengan kod semasa, kod semasa dan `Rumah_A_Predictor_MASTER_CONTEXT.md` mengambil keutamaan.
