# Rumah A Predictor — Master Context

Dokumen ini ialah rujukan utama keadaan semasa projek. Jika dokumen lama bercanggah dengannya, gunakan kod semasa dan arahan terbaru pemilik.

## 1. Identiti dan tujuan

- **Platform:** Streamlit Cloud
- **Repositori:** `wazley-hub/rumah-a-predictor-v9`
- **Sumber aktif:** `TotoHistoryAll.xlsx`
- **Tujuan:** mencari corak, mengaudit formula dan mengecilkan ruang nombor berdasarkan keputusan sejarah.

Projek tidak mendakwa boleh menjamin masa hadapan. Falsafah pemilik ialah membetulkan bacaan kesilapan lalu untuk mendapatkan analisis masa hadapan yang lebih baik.

## 2. Prinsip wajib

1. Bridge V1 dan V2 ialah generator calon utama.
2. Hit dinilai berdasarkan digit penuh tanpa mengira susunan.
3. Setiap engine mesti kekal berasingan.
4. Jangan campurkan Carta, family, Pair Shortlist atau Selection Engine ke dalam 2D Carry tanpa audit khusus.
5. Jangan mencipta rule, skor atau ranking yang tidak diminta.
6. Audit mesti walk-forward dan bebas data target.
7. Nombor yang melepasi satu penapis dianggap sama rata kecuali pengguna meminta audit pemilihan lain.
8. Blok baharu tidak boleh menggantikan blok lama tanpa arahan jelas.
9. UI perlu ringkas; senarai besar dan audit diletakkan dalam expander.
10. Perubahan produksi mesti diuji sebelum diterbitkan.

## 3. Data

### TotoHistoryAll.xlsx

Mengandungi Draw No, Draw Date, 1st, 2nd dan 3rd Prize. Digunakan oleh Generate, History Manager, Bridge, 2D Carry dan backtest.

### TotoFullResult.xlsx

Mengandungi Top 3, Special dan Consolation. Digunakan untuk audit luar atau eksperimen khusus. Ia tidak dibaca dalam aliran Generate utama.

## 4. Formula Bridge

### Bridge V1

```text
base pair + 1 missing digit + 1 existing digit
```

### Bridge V2

```text
base pair + 2 missing digit
base pair + 2 existing digit
```

Dua digit tambahan V2 mestilah berbeza. Base pair songsang yang membawa set digit sama dideduplikasi. Bridge menjana ruang nombor dan tidak menentukan nombor terbaik.

## 5. 2D Carry Engine

### Objektif

Menguji idea bahawa dua digit daripada keputusan 2nd Prize sering dibawa ke Top 3 draw berikutnya.

Daripada nombor empat digit `ABCD`, semua enam kedudukan ialah:

```text
1+2 = AB
1+3 = AC
1+4 = AD
2+3 = BC
2+4 = BD
3+4 = CD
```

Susunan digit diabaikan semasa padanan. Contohnya `86` boleh sepadan dengan `68`.

### Output pertama: semua 2D Carry

- Ambil semua gabungan dua digit unik daripada 2nd Prize.
- Tapis calon Bridge V1 dan V2 yang mengandungi sekurang-kurangnya satu gabungan.
- Paparkan V1 dan V2 secara berasingan.
- Sediakan `Copy Semua 2D Carry`.
- Tiada ranking nombor.

### Output kedua: 2D Carry Pilihan Kedudukan

- Audit enam kedudukan menggunakan 100 transisi terdahulu.
- Kira berapa kali dua digit pada setiap kedudukan dibawa ke Top 3 berikutnya.
- Pilih satu kedudukan dengan jumlah carry tertinggi.
- Gunakan dua digit semasa daripada kedudukan itu untuk menapis Bridge.
- Paparkan dalam blok, butang Copy dan expander yang berasingan.
- Semua nombor dalam hasil akhir dianggap sama rata.

### Dapatan audit 100 draw

```text
Dua digit 2nd dibawa ke Top 3: 70/100
Carry + nombor penuh tersedia dalam Bridge: 61/100
Liputan Bridge apabila carry berlaku: 61/70 (87.1%)
```

Audit kedudukan:

```text
2+4: 30/100
2+3: 27/100
3+4: 27/100
1+4: 24/100
1+2: 22/100
1+3: 19/100
```

Nilai ini ialah kekerapan sejarah, bukan jaminan dan bukan skor nombor.

### Contoh disahkan

Sumber 2nd Prize `4816` menghasilkan:

```text
48 / 41 / 46 / 81 / 86 / 16
```

Pada draw berikutnya:

- `86` muncul sebagai `68` dalam `3628`;
- `3628` tersedia dalam Bridge V1;
- `16` muncul dalam `2126`;
- `2126` tidak tersedia dalam Bridge bagi draw tersebut.

Untuk 2nd Prize `4030`, kedudukan audit tertinggi ialah `2+4 = 00`. Penapis semasa mengecilkan output kepada 4 V1 dan 26 V2, tanpa meranking 30 nombor tersebut.

## 6. Komponen aktif lain

### Selection Engine

Eksperimen Top 10 berasaskan rekod Pair Slot dengan lookback 100 draw. Ia kekal berasingan daripada 2D Carry. Audit terbaru menunjukkan formula slot sering meletakkan nombor pemenang jauh di bawah, maka ia tidak boleh dianggap penentu utama.

### Bridge Pair Shortlist

Paparan nombor Bridge mengikut pair. Ranking pair lama ialah rujukan eksperimen dan tidak mempengaruhi 2D Carry.

### Bridge Dua Pair

Penapis tambahan berdasarkan kehadiran pair kedua. Kekal sebagai blok berasingan.

### Carta 3D V2

Rujukan visual Menegak dan L. Carta tidak mengubah Bridge, Selection atau 2D Carry.

### Backtest

Mengukur Bridge V1 Hit, Bridge V2 Hit dan hit unik. Menggunakan cache serta menghasilkan Quick Review, Summary dan Detail.

## 7. Komponen legasi tidak aktif

- AI Pick, Strong Buy dan Backup
- empat model utama lama
- Family Ranker V1/V2
- Combined Family Ranker
- Meta Ranker
- Core Family Consensus
- Fourth Digit Completion
- Conditional Route Selector
- DDE dalam backtest utama
- Signal Lab
- Result Chart Board V3.1
- Top 10 Lintas Bulan

Jangan hidupkan semula hanya kerana fail audit lama masih menyebutnya.

## 8. Aliran penggunaan

1. Kemas kini keputusan Top 3.
2. Simpan history ke GitHub.
3. Tekan Generate.
4. Semak Bridge V1 dan V2.
5. Semak semua 2D Carry.
6. Semak 2D Carry Pilihan Kedudukan sebagai penapis tambahan.
7. Gunakan Copy bagi blok yang diperlukan.
8. Selepas result dibuka, rekodkan hit dan kegagalan secara jujur.

## 9. Infrastruktur

Streamlit membaca branch utama GitHub. Auto-save memerlukan token dengan:

```text
Repository permissions → Contents → Read and write
```

Metadata kekal Read-only seperti yang diwajibkan GitHub.

## 10. Arahan untuk AI

- Baca kod semasa sebelum mencadangkan perubahan.
- Jangan menganggap sesuatu lebih kuat tanpa audit.
- Jangan menggantikan output sedia ada apabila pengguna meminta tambahan.
- Jangan menggabungkan dua engine secara sesuka hati.
- Bezakan dengan jelas generator, penapis, rujukan dan eksperimen.
- Jika pengguna meminta ranking, nyatakan tepat apa yang diranking.
- Kekalkan perubahan kecil, boleh diuji dan boleh dipulihkan.

**Ringkasan:** Rumah A Predictor ialah sistem Bridge-first yang menggunakan 2D Carry sebagai penapis berasingan untuk mengecilkan ruang calon berdasarkan dua digit daripada keputusan 2nd Prize.
