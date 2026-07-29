# Changelog

Perubahan penting Rumah A Predictor direkodkan di sini. Changelog versi lama yang terperinci disimpan dalam `docs/archive/`.

## Semasa — 29 Julai 2026

### Ditambah

- **Selection Engine**
  - Menghasilkan Pilihan 10 daripada calon Bridge.
  - Menggunakan Pair Slot dengan lookback tetap 100 draw.
  - Tidak menggunakan Carta, family atau ranking legasi.

- **Bridge V2**
  - Menjana laluan `base pair + 2 digit missing`.
  - Menjana laluan `base pair + 2 digit existing`.
  - Mengekalkan digit tambahan yang berbeza.

- **Bridge Pair Shortlist**
  - Audit pair menggunakan 100 draw terkini.
  - Setiap pair mempunyai expander tersendiri.
  - Nombor Bridge V1 dan V2 bagi pair tersebut boleh dilihat dan disalin secara berasingan.

- **Bridge Dua Pair**
  - Menunjukkan calon Bridge yang turut mempunyai sokongan pair kedua.
  - Kekal sebagai rujukan berasingan.

- **Carta 3D V2**
  - Paparan Menegak dan L.
  - Butang Copy Carta dikekalkan.
  - Carta kekal sebagai rujukan dan tidak mengubah Selection Engine.

### Diubah

- Seni bina app dipermudah kepada pendekatan **Bridge-first**.
- Bridge V1 dan V2 dikekalkan sebagai generator utama.
- Base pair songsang yang membawa digit sama dideduplikasi, contohnya `13` dan `31`.
- Selection Engine ditetapkan kepada **100 draw**, bukan 300 draw.
- Hit dinilai menggunakan digit penuh tanpa mengira susunan.
- Butang utama dipendekkan kepada **Generate**.
- Gaya butang Copy diseragamkan.
- UI dikemas kini dengan kad engine, warna yang lebih jelas dan susun atur mesra telefon.
- Output besar diletakkan dalam expander untuk mengurangkan keserabutan.
- Master Context ditulis semula supaya mencerminkan keadaan app semasa.
- README dikemas kini kepada penerangan profesional tentang sistem Bridge-first.
- Struktur root repositori dibersihkan; fail versi lama dipindahkan ke `docs/archive/`.

### Prestasi dan kestabilan

- Backtest Bridge menggunakan cache supaya draw lama tidak dikira semula tanpa sebab.
- Paparan backtest diringkaskan kepada:
  - Quick Review
  - Summary
  - Detail
- DDE dikeluarkan daripada backtest utama.
- Kolum hit berulang V2 Ranker dibuang.
- Proses family dan ranker legasi tidak lagi dijalankan semasa Generate.
- Initial load dan aliran Generate tidak lagi membaca semua audit lama.

### Dibuang atau dinyahaktifkan

Komponen berikut tidak lagi menjadi sebahagian daripada aliran aktif:

- AI Pick
- Top 3 AI
- Strong Buy
- Backup Pool
- Empat model utama lama
- Family Ranker V1
- Family Ranker V2
- Combined Family Ranker
- Meta Ranker
- Core Family Consensus
- Fourth Digit Completion
- Conditional Route Selector
- DDE dalam backtest utama
- Signal Lab teknikal
- Result Chart Board V3.1
- pengesahan Carta menggunakan full result
- Top 10 Lintas Bulan kerana hanya relevan pada peralihan bulan dan tidak sesuai sebagai pilihan setiap draw

Kod legasi family dan ranking yang tidak digunakan telah dibuang daripada aliran pelaksanaan supaya tidak mempengaruhi engine baharu.

### Data

- `TotoHistoryAll.xlsx` kekal sebagai sumber aktif keputusan Top 3.
- History Manager menyokong tambah, kemas kini, carian dan simpan ke GitHub.
- `TotoFullResult.xlsx` disimpan untuk audit tambahan dan tidak dibaca dalam aliran Generate utama.
- Auto-save GitHub menggunakan token dengan kebenaran `Contents: Read and write`.

### Dokumentasi

- `README.md` menerangkan:
  - tujuan projek;
  - engine aktif;
  - aliran analisis;
  - pengurusan data; dan
  - prinsip pembangunan.
- `Rumah_A_Predictor_MASTER_CONTEXT.md` kini menjadi rujukan utama untuk menyambung projek dalam chat baharu.
- Changelog versi pembangunan terperinci disimpan dalam `docs/archive/`.

## Sejarah ringkas

### V31 — Julai 2026

- Bridge V1 dan V2 dijadikan fokus utama.
- Pelbagai family ranker, combined dan meta telah diaudit sebelum dinyahaktifkan.
- Carta 3D, Pair Shortlist, Selection Engine dan backtest pantas dibangunkan.
- UI dibersihkan dan dokumentasi repositori disusun semula.

### V30 — Jun 2026

- Penyelarasan history dan pembetulan Draw No.
- Pengurusan data GitHub diperkukuh.
- Asas deployment Streamlit distabilkan.

### V27 — fasa UI awal

- Update Keputusan dipisahkan daripada History Manager.
- Home disusun semula.
- Tajuk berulang dibuang.
- Update keputusan tidak lagi auto-expand.

---

Untuk keadaan teknikal dan peraturan projek yang terkini, rujuk `Rumah_A_Predictor_MASTER_CONTEXT.md`. Jika changelog arkib bercanggah dengan kod semasa, kod semasa dan Master Context mengambil keutamaan.
