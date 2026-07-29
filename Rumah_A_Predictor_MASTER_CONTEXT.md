# Rumah A Predictor — Master Context

Dokumen ini ialah rujukan utama untuk memahami keadaan semasa Rumah A Predictor. Ia menggantikan konteks lama yang masih menerangkan AI Pick, Strong Buy, model keluarga dan aliran ramalan legasi.

## 1. Identiti projek

**Nama:** Rumah A Predictor  
**Platform utama:** Streamlit Cloud  
**Repositori:** `wazley-hub/rumah-a-predictor-v9`  
**Pengguna utama:** Pemilik projek  
**Status:** Aktif, digunakan untuk analisis dan kajian sejarah

Rumah A Predictor ialah alat kajian nombor berasaskan keputusan lampau. Ia dibina untuk mencari corak, memahami struktur nombor rawak, mengaudit formula dan membetulkan kelemahan bacaan sejarah.

Ia bukan sistem yang mendakwa boleh melihat atau menjamin masa depan. Prinsip pemilik projek ialah:

> Bukan meramal masa depan semata-mata; membetulkan kesilapan lalu untuk mendapatkan bacaan masa depan yang lebih baik.

Keputusan sebenar tetap dipengaruhi oleh rawak, nasib dan tindakan pengguna.

## 2. Prinsip teras

1. **Bridge ialah asas utama.** Semua kajian pemilihan mesti bermula daripada nombor yang benar-benar dihasilkan oleh Bridge V1 atau Bridge V2.
2. **Susunan digit tidak menentukan hit analisis.** Jika digit penuh sama, nombor dianggap sepadan walaupun susunannya berbeza. Contoh: `4123` sepadan dengan `4132`.
3. **Pair tidak boleh dipecahkan ketika menyusun nombor.** Jika pair `13` digunakan, bentuk seperti `13xx`, `x13x` dan `xx13` dibenarkan; susunan dalaman `13` mesti kekal.
4. **Setiap engine mesti kekal berasingan.** Carta, Selection Engine, Pair Shortlist dan eksperimen baharu tidak boleh mempengaruhi satu sama lain tanpa audit khusus.
5. **Tiada family dalam aliran pemilihan aktif.** Konsep family digit lama, Family Ranker, Combined Ranker dan Meta Ranker tidak digunakan untuk memilih nombor.
6. **Walk-forward sahaja.** Audit hanya boleh menggunakan maklumat yang tersedia sebelum target draw.
7. **Tiada data leakage.** Keputusan target atau masa hadapan tidak boleh digunakan semasa membina pilihan untuk target tersebut.
8. **Ringkas lebih baik.** Jangan tambah rule, skor atau ranking yang tidak diminta dan tidak dapat dijelaskan.
9. **Engine baharu diuji secara berasingan.** Jangan mengubah engine sedia ada semata-mata untuk memasukkan idea baharu.
10. **UI mesti mudah dibaca dan pantas.** Nota teknikal, jadual besar dan bahagian audit hendaklah disembunyikan atau diletakkan dalam expander jika tidak diperlukan setiap hari.

## 3. Sumber data

### `TotoHistoryAll.xlsx`

Sumber data aktif aplikasi. Mengandungi:

- Draw No
- Draw Date
- 1st Prize
- 2nd Prize
- 3rd Prize

Fail ini digunakan oleh:

- paparan keputusan terkini;
- History Manager;
- Bridge dan alat berkaitan;
- Selection Engine;
- Pair Shortlist;
- backtest Bridge; dan
- auto-save GitHub.

### `TotoFullResult.xlsx`

Mengandungi keputusan penuh termasuk Special dan Consolation. Fail ini disimpan untuk audit tambahan atau eksperimen luar app.

Ia **bukan sumber utama aliran Generate semasa** dan tidak boleh mempengaruhi Selection Engine tanpa satu kajian baharu yang jelas.

## 4. Aliran penggunaan harian

1. Semak keputusan terbaru.
2. Kemas kini Top 3 melalui History Manager jika perlu.
3. Pastikan `TotoHistoryAll.xlsx` telah disimpan ke GitHub.
4. Tekan **Generate**.
5. Baca setiap output secara berasingan.
6. Gunakan butang Copy pada bahagian yang diperlukan.
7. Selepas keputusan seterusnya dibuka, semak sama ada Bridge atau shortlist menghasilkan digit penuh.
8. Gunakan Backtest hanya untuk menguji sejarah, bukan untuk mengubah keputusan draw yang sudah diketahui.

## 5. Engine dan komponen aktif

### 5.1 Bridge V1

Formula asas:

```text
base pair + 1 digit missing + 1 digit existing
```

Base pair diambil daripada pair depan, tengah dan belakang keputusan Top 3 terkini.

Pair songsang yang mewakili digit sama tidak diulang sebagai base pair berasingan. Contohnya `13` dan `31` dikira sebagai keluarga pair yang sama untuk tujuan deduplikasi base pair.

Bridge V1 ialah generator utama, bukan ranker.

### 5.2 Bridge V2

Dua laluan:

```text
base pair + 2 digit missing
base pair + 2 digit existing
```

Dua digit tambahan mestilah berbeza. Bridge V2 melengkapkan ruang yang tidak dihasilkan oleh V1, khususnya struktur dua missing atau dua existing.

Bridge V1 dan V2 tidak boleh dinilai seolah-olah bersaing. Kedua-duanya ialah laluan liputan yang berbeza.

### 5.3 Selection Engine

Selection Engine menghasilkan **Pilihan 10** daripada calon Bridge.

Keadaan semasa:

- lookback tetap: **100 draw**;
- input pemilihan: **Pair Slot**;
- audit: walk-forward;
- hit dinilai mengikut digit penuh tanpa mengira susunan;
- Carta dan family tidak dimasukkan;
- output Selection Engine tidak mengubah Bridge.

Audit rujukan yang membawa kepada engine ini:

- Bridge V1 atau V2 menangkap kira-kira 83 daripada 100 target draw dalam audit berkaitan;
- Top 10 menangkap 10 daripada 83 Bridge-hit;
- kadar tersebut bukan jaminan draw seterusnya—hit boleh berlaku pada mana-mana draw dalam siri akan datang.

Jangan menambah Carta, family, Meta atau signal lain ke dalam Selection Engine ini tanpa membuka aliran eksperimen baharu.

### 5.4 Bridge Pair Shortlist

Tujuan:

- menyusun sembilan kedudukan pair semasa mengikut sokongan sejarah;
- membolehkan pengguna membuka mana-mana pair;
- memaparkan nombor Bridge V1 dan V2 yang benar-benar datang daripada pair tersebut;
- menyediakan butang Copy bagi setiap pair.

Lookback semasa: **100 draw**.

Ranking pair ialah bantuan memilih kawasan Bridge. Ia bukan jaminan bahawa pair #1 mesti digunakan pada setiap draw.

### 5.5 Bridge Dua Pair

Blok tambahan yang menapis nombor Bridge berdasarkan kehadiran pair kedua daripada keputusan semasa.

Ia:

- tidak menggantikan Pair Shortlist;
- tidak mengubah Selection Engine;
- tidak menggunakan family sebagai ranking; dan
- kekal sebagai rujukan sokongan.

### 5.6 Carta 3D V2

Carta ialah kaedah pemerhatian visual yang diinspirasikan oleh cara tradisional membaca bentuk seperti:

- Menegak;
- L;
- I;
- T;
- Z/S; dan
- 2×2.

Paparan aktif menumpukan pilihan 3D Menegak dan L.

Carta:

- berasal daripada operasi jumlah dan campur silang keputusan Top 3;
- boleh memberi 3D seperti `113`, kemudian dibaca jalan depan dan belakang seperti `113` dan `311`;
- tidak dipaksa masuk ke Selection Engine;
- tidak boleh dianggap gagal hanya kerana 3D tersebut tiada dalam Bridge;
- hanya mendapat pelengkap 4D apabila kebetulan terdapat padanan dalam Bridge.

Carta kekal sebagai rujukan visual dan mempunyai butang Copy sendiri.

### 5.7 Backtest Bridge V1 + V2

Backtest aktif mengukur:

- Bridge V1 Hit;
- Bridge V2 Hit;
- Bridge V1 atau V2 Hit;
- kadar hit unik;
- nombor hit bagi setiap draw.

Paparan dan fail muat turun mestilah ringkas:

- `Quick Review`
- `Summary`
- `Detail`

DDE dan ranker family tidak perlu dimasukkan semula.

Backtest menggunakan cache supaya draw lama tidak dikira semula tanpa sebab.

## 6. Kajian mingguan

Definisi minggu yang betul:

```text
Ahad hingga Sabtu
```

Draw biasa lazimnya berlaku pada:

- Ahad
- Rabu
- Sabtu

Special Draw boleh berlaku pada Selasa atau hari tambahan lain dan masih dikira dalam minggu Ahad–Sabtu yang sama.

Minggu tidak dipotong apabila bulan berubah. Contohnya Ahad hujung Jun, Rabu awal Julai dan Sabtu awal Julai masih satu kitaran mingguan.

Audit Top 10 mingguan:

- signal hanya mula tersedia selepas satu transisi dalam minggu diketahui;
- draw ketiga: 3 hit daripada 46 signal untuk kaedah terbaik;
- draw keempat selepas Special Draw: 0 hit daripada 6 sampel;
- belum layak menjadi engine utama.

Kajian mingguan kekal di luar UI sehingga terdapat peningkatan yang jelas.

## 7. Komponen legasi yang tidak aktif

Komponen berikut tidak lagi menjadi sebahagian daripada aliran pemilihan:

- AI Pick
- Top 3 AI
- Strong Buy
- Backup Pool
- Model Statistik
- Model Peralihan Posisi
- Model Pasangan lama
- Model No Double
- Core Family Consensus
- Fourth Digit Completion
- Family Ranker V1/V2
- Combined Family Ranker
- Meta Ranker
- Conditional Route Selector
- DDE dalam backtest utama
- Result Chart Board V3.1
- Signal Lab teknikal
- Top 10 Lintas Bulan

Jangan hidupkan semula komponen ini hanya kerana kod, changelog atau fail audit lama masih menyebutnya.

## 8. Peraturan perubahan app

Sebelum mengubah app:

1. Kenal pasti sama ada permintaan ialah audit, eksperimen atau perubahan produksi.
2. Jangan menyentuh engine lama jika pengguna meminta blok baharu.
3. Audit idea di luar app terlebih dahulu kecuali pengguna jelas meminta ia terus dimasukkan.
4. Bandingkan output dengan formula Bridge sebenar.
5. Uji sintaks dan output nombor.
6. Pastikan initial load dan backtest tidak menjadi perlahan.
7. Terbitkan ke GitHub hanya selepas ujian lulus.
8. Jangan paparkan nota teknikal panjang dalam UI.
9. Kekalkan emoji dan gaya butang secara seragam.
10. Jangan menukar nama atau URL app tanpa arahan pengguna.

## 9. Perkara yang mesti dielakkan oleh AI

- Jangan mencipta rule tambahan kerana mahu menjadikan sistem kelihatan lebih pintar.
- Jangan menganggap ranking tertinggi semestinya pilihan betul.
- Jangan mencampurkan dua engine hanya kerana kedua-duanya mempunyai output serupa.
- Jangan menggunakan keputusan target semasa mengira pilihan target itu.
- Jangan mengembangkan shortlist sehingga lebih banyak daripada Bridge asal.
- Jangan menyebut sesuatu hit jika digit sebenarnya tidak sepadan.
- Jangan membaca nombor daripada gambar secara cuai.
- Jangan mendakwa kadar Bridge ialah kadar kejayaan Top 10.
- Jangan menganggap full result aktif dalam app jika audit itu hanya dijalankan di luar.
- Jangan menggantikan falsafah pemilik dengan model ramalan generik.

## 10. Infrastruktur

### GitHub

Repositori menyimpan:

- `app.py`
- `requirements.txt`
- dua fail keputusan Excel;
- README;
- Master Context;
- changelog utama; dan
- arkib dokumen lama dalam `docs/`.

### Streamlit Cloud

Streamlit membaca kod dan data daripada repositori GitHub. Perubahan pada `main` akan mencetuskan deployment semula.

Auto-save keputusan memerlukan `GITHUB_TOKEN` dalam Streamlit Secrets dengan kebenaran:

```text
Repository permissions → Contents → Read and write
```

Metadata kekal Read-only seperti yang diwajibkan oleh GitHub.

### Fail keputusan penuh

`TotoFullResult.xlsx` tidak perlu dibaca pada setiap load. Ia hanya patut digunakan apabila audit full-result benar-benar diperlukan.

## 11. Keutamaan semasa

1. Kekalkan Bridge V1 dan V2 stabil.
2. Pastikan Selection Engine menggunakan 100 draw sahaja.
3. Pantau Top 10 biasa tanpa mencampurkannya dengan Carta.
4. Kaji cara mengecilkan pilihan Bridge tanpa family dan tanpa rule kompleks.
5. Pastikan app kekal kemas, pantas dan mudah digunakan pada telefon.
6. Rekod keputusan audit dengan jujur, termasuk kegagalan.

## 12. Arahan apabila membuka chat baharu

Jika dokumen ini diberikan kepada AI dalam chat baharu:

- anggap kandungannya lebih terkini daripada changelog versi lama;
- jangan kembali kepada struktur V27.5 atau AI Pick;
- baca `README.md` dan kod `app.py` semasa sebelum membuat perubahan;
- sahkan formula melalui audit, bukan andaian;
- hormati pemisahan antara Bridge, Selection, Pair, Carta dan eksperimen;
- kekalkan perubahan kecil, boleh diuji dan boleh dipulihkan;
- jika arahan pengguna bercanggah dengan dokumen ini, ikut arahan terbaru pengguna.

---

**Ringkasan satu ayat:** Rumah A Predictor ialah sistem analisis Bridge-first yang menjana ruang nombor daripada pair Top 3, kemudian menguji kaedah mengecilkan ruang itu melalui laluan yang berasingan, ringkas dan boleh diaudit.
