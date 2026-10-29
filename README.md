# Rumah A Predictor

> Aplikasi analisis nombor berasaskan sejarah keputusan Top 3, struktur pasangan digit dan ujian terhadap peluang rawak.

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Status](https://img.shields.io/badge/Status-Active-159957)](#status-projek)

## Gambaran keseluruhan

Rumah A Predictor ialah ruang kerja analisis untuk mengkaji bagaimana digit dan pasangan digit daripada keputusan Top 3 terdahulu membentuk kumpulan nombor bagi draw seterusnya.

Projek ini **tidak mendakwa boleh meramal masa depan**. Cabutan ialah proses rawak. Tujuan app ialah:

- menjana ruang nombor secara konsisten melalui Bridge V1 dan V2;
- mengecilkan ruang itu melalui Route Signal dan ranking pair yang berubah mengikut draw terkini;
- menunjukkan nombor yang baru naik datang daripada engine dan laluan mana; dan
- menguji setiap enjin terhadap **peluang rawak**, supaya hit rate yang nampak tinggi tidak disalah faham.

## Rupa app

Reka bentuk mengikut gaya aplikasi mudah alih kewangan di Malaysia: latar biru-kelabu cerah, kad putih bersudut bulat, satu kad utama berwarna biru tua, fon geometri dan nombor besar.

| Perkara | Pilihan |
|---|---|
| Warna | Biru Rumah `#1456D8`, Biru Tua `#0A2463`, kuning `#FFC72E` (hadiah pertama sahaja), latar `#ECF0F8`, teks `#0D1B3A` |
| Fon | Plus Jakarta Sans (dimuat dari Google Fonts; jika gagal, fon sistem) |
| Elemen utama | Kad keputusan terkini berwarna biru tua dengan 1st, 2nd, 3rd |
| Komponen | jubin signal, cip hijau bagi engine yang menjana, tab berbentuk pil, butang Generate penuh lebar |

Semua gaya ada dalam `ui_theme.py`. `.streamlit/config.toml` menetapkan tema cerah supaya komponen Streamlit tidak bertukar gelap pada peranti mod gelap. Untuk kembali kepada rupa asal Streamlit, buang panggilan `apply_theme(st)` dalam `app.py`.

## Susun atur app

```text
Kad keputusan terkini                 <- Draw, tarikh, 1st / 2nd / 3rd, status sambungan
Nombor terkini naik daripada mana     <- engine/laluan yang menjana 1st, 2nd, 3rd
Generate                              <- masukkan Top 3, tekan Generate
Ringkasan Signal                      <- Route Signal 1st/2nd/3rd, Bridge, Laluan, Top-N nombor
Tab:  Route | Match | Bridge V1 | Bridge V2 | Lanjutan
Alat & Data:  📚 Sejarah Keputusan | 🧪 Ujian & Backtest
```

Hasil Generate kekal walaupun pilihan (dropdown) ditukar. Hasil yang dipaparkan sentiasa menyatakan draw yang digunakan.

## Komponen

| Komponen | Fungsi |
|---|---|
| **Bridge V1** | Base pair + satu digit missing + satu digit existing. |
| **Bridge V2** | Base pair + dua digit missing atau dua digit existing. |
| **Ranking pair dinamik** | Pair V1 dan V2 disusun berasingan daripada skor tertinggi. Skor = peluang rawak pair itu pada draw semasa × *lift* berpemberat susut-masa. Susunan berubah mengikut draw terkini. |
| **Nombor dalam pair** | Setiap pair menunjukkan nombor disusun ikut peluang box dan kekerapan terkini, dengan had Top 10 / 20 / 30 / Semua. |
| **Route Signal** | Untuk 1st, 2nd dan 3rd, memilih laluan **V1 · Missing** atau **V2 · Pair** (atau "Tiada pilihan") berdasarkan keadaan sejarah yang serupa, dengan sokongan keadaan 0 hingga 4. Undian guna *lift* (hit dibahagi jangkaan liputan), bukan hit rate mentah, supaya laluan yang calonnya lebih banyak tidak menang hanya kerana liputan. |
| **Top-N Route Terpilih** | Calon laluan terpilih digabung, satu baris bagi setiap keluarga box, disusun ikut skor konsensus. Pilih Top 5 / 10 / 15 / 20 / 30. |
| **Match Engine** (tab sendiri) | Quattro (4/4), Triple (3/4), Double (2/4) dan Bridge Solo (1/4): Bridge disemak terhadap sokongan engine 2D. Jadual ringkas semua tahap, pilih tahap dan had nombor; tahap yang dipilih signal dibuka secara lalai, V1 dan V2 boleh disalin terus. |
| **1st / 2nd / 3rd 2D Engine** | Enjin 2D sokongan dalam tab Lanjutan. Setiap enjin menunjukkan satu jadual pair dan satu pemilih pair (gaya sama seperti Bridge V1/V2), serta audit sejarah 100 draw. |
| **Carta 3D V2** | Rujukan visual Menegak dan L (dalam tab Lanjutan). |
| **Nombor terkini naik daripada mana** | Menyemak ramalan yang dibuat daripada draw sebelumnya terhadap keputusan terkini: engine mana yang menjana setiap hadiah, beserta laluan dan kedudukan pair. |

## Cara membaca skor

| Lajur | Maksud |
|---|---|
| **Liputan %** | Peratus ruang 0000–9999 yang dilindungi senarai calon, dengan padanan box. |
| **Rawak %** | Peluang sekurang-kurangnya satu calon kena jika nombor dipilih secara rawak dengan liputan yang sama. |
| **Lift** | Hit sebenar dibahagi jangkaan rawak. Nilai hampir 1.0 bermakna tiada kelebihan. |
| **Skor %** | Rawak % × Lift. Digunakan untuk susunan, bukan kebarangkalian yang disahkan. |

**Padanan box** bermaksud digit boleh disusun semula (3170 sama dengan 7103), jadi satu calon meliputi sehingga 24 nombor. Hit rate box yang tinggi sering sama dengan jangkaan rawak. Bandingkan sentiasa dengan lajur Rawak %.

## Ujian dan keputusan semasa

App menyediakan alat ujian dalam **Alat & Data → Ujian & Backtest**:

| Alat | Fungsi |
|---|---|
| **Backtest Bridge V1 + V2** (Turbo Lite) | Backtest Bridge, dengan jadual perbandingan peluang rawak dan laporan Excel. |
| **Backtest vs Rawak (Top-K, walk-forward)** | Menguji strategi pilih K nombor terhadap peluang rawak pada sehingga 3,000 draw, dengan p-value dan p terlaras. |
| **Diagnostik Ranking Pair** | Menguji sama ada ranking pair berubah mengikut draw dan sama ada ranking teratas benar-benar hit lebih kerap. |

Keputusan ujian pada data sehingga Oktober 2026 (jalankan semula bila data bertambah):

| Ujian | Keputusan |
|---|---|
| Bridge V1 dan V2 (kira-kira 100 draw) | Box 51.0% dan 55.6% berbanding jangkaan rawak 52.8% dan 56.0%. Tiada kelebihan. |
| Top 10 nombor, walk-forward 2,000 draw (kekerapan, overdue, skor digit) | Exact 0.25–0.40% berbanding rawak 0.30–0.45%. Tiada strategi mengalahkan rawak. |
| Route Signal lama dan baru (500 draw) | Kedua-duanya sama dengan rawak. Route baru memilih dengan lebih adil dan senarainya lebih pendek, tetapi tidak lebih tepat. |
| Ranking pair dinamik (500 draw) | Slot teratas berubah pada 84% draw (kaedah lama 9.8%). Ranking 1 hit 25.6% berbanding rawak 23.9%, tidak signifikan. |
| Top 10 konsensus | Nampak baik pada 500 draw (8.7% berbanding 6.1%), tetapi tidak berulang pada 1,000 draw sebelumnya (5.1% berbanding 6.2%). Kebetulan. |

Kesimpulan semasa: tiada enjin dalam app ini menunjukkan kelebihan yang sah terhadap peluang rawak. Susunan, ranking dan Top-N ialah alat untuk menyusun dan mengaudit, bukan ramalan.

## Aliran analisis

```text
Keputusan Top 3 terkini
        │
        ├── Base pair unik
        │       ├── Bridge V1 ──┐
        │       └── Bridge V2 ──┤── Ranking pair dinamik (skor tertinggi dahulu)
        │                       │
        ├── Route Signal 1st / 2nd / 3rd (undian ikut lift)
        │       └── Top-N Route Terpilih + Match Engine
        │
        ├── Enjin 2D 1st / 2nd / 3rd + Carta 3D V2     (tab Lanjutan)
        │
        └── Semakan draw sebelumnya: "naik daripada mana"
```

Setiap laluan mempunyai tujuan tersendiri dan tidak digabungkan secara automatik, supaya satu pemerhatian tidak mengubah keputusan laluan lain.

## Pengurusan data

| Fail | Kegunaan |
|---|---|
| `TotoHistoryAll.xlsx` | Sejarah Draw No, tarikh dan keputusan Top 3. Dibaca oleh app. |
| `TotoFullResult.xlsx` | Keputusan penuh termasuk Special dan Consolation. Disimpan untuk rujukan; app semasa tidak membacanya. |

History Manager (Alat & Data → Sejarah Keputusan) membolehkan pengguna:

- menambah atau mengemas kini keputusan;
- mencari dan mengedit draw tertentu;
- memadam rekod yang tidak diperlukan; dan
- menyimpan perubahan ke repositori GitHub apabila **Auto-save ke GitHub** dipilih.

Auto-save memerlukan `GITHUB_TOKEN` dalam Streamlit Secrets. Tanpa token, app menggunakan fail `TotoHistoryAll.xlsx` dalam repositori. Tindakan padam tidak boleh dibatalkan selepas auto-save.

Backtest menyimpan cache baris dalam `.backtest_row_cache_v31_55_bridge_solo.json` supaya hanya draw baharu dikira semula.

### Nama fail muat turun

| Fail | Contoh |
|---|---|
| Laporan backtest Excel | `Rumah_A_Backtest_Draw620326_30draw.xlsx` |
| Keputusan Backtest vs Rawak | `Rumah_A_Backtest_vs_Rawak_Top10_2000draw.csv` |
| Sejarah semasa | `TotoHistoryAll_current_app.xlsx` |

## Menjalankan secara tempatan

```bash
pip install -r requirements.txt
streamlit run app.py
```

Selepas app dibuka:

1. Semak keputusan terkini dan jadual **Nombor terkini naik daripada mana**.
2. Masukkan tiga keputusan Top 3 dan tekan **Generate**.
3. Baca **Ringkasan Signal** di atas, kemudian semak tab Route Signal, Bridge V1 dan Bridge V2.
4. Gunakan **Ujian & Backtest** untuk membandingkan sebarang pemerhatian dengan peluang rawak.

## Ujian automatik

```bash
python smoke_test_app.py          # jalankan app penuh dengan Streamlit palsu; semak ralat, expander bersarang, widget berganda
FORCE_BUTTONS=run_backtest_turbo_v31_7,run_wf_bt,run_pair_diag python smoke_test_app.py   # tekan butang Backtest dan Diagnostik juga
python test_backtest_baseline.py  # peluang rawak, p-value, tiada kebocoran data dalam walk-forward
python test_ranking_engine.py     # ranking dinamik, lift laluan, tiada kebocoran masa hadapan
python test_latest_origin.py      # penjelasan asal nombor terkini dan nama fail
python test_ui_theme.py           # komponen HTML tema: tarikh, escape, jubin signal
```

Backtest top-K boleh dijalankan sendiri tanpa app:

```bash
python backtest_baseline.py TotoHistoryAll.xlsx --draws 2000 --k 10
```

`smoke_test_app.py` tidak menggantikan ujian dalam Streamlit sebenar; ia menangkap ralat aliran, bukan rupa paparan.

## Struktur repositori

```text
.
├── app.py                     # UI Streamlit dan enjin Bridge / Route Signal / 2D
├── backtest_baseline.py       # backtest vs peluang rawak, p-value, walk-forward top-K
├── ranking_engine.py          # ranking pair dinamik, lift laluan, shortlist konsensus
├── latest_origin.py           # asal nombor terkini naik dan nama fail muat turun
├── ui_theme.py                # tema visual: CSS dan komponen kad / jubin
├── .streamlit/
│   └── config.toml            # tema cerah Streamlit
├── smoke_test_app.py          # ujian asap app penuh
├── test_backtest_baseline.py
├── test_ranking_engine.py
├── test_latest_origin.py
├── test_ui_theme.py
├── requirements.txt
├── TotoHistoryAll.xlsx
├── TotoFullResult.xlsx
├── README.md
└── CHANGELOG.md
```

`app.py` mengimport `backtest_baseline.py`, `ranking_engine.py`, `latest_origin.py` dan `ui_theme.py`. Keempat-empatnya mesti berada dalam folder yang sama.

## Prinsip pembangunan

- **Bridge-first**: Bridge V1 dan V2 ialah generator utama.
- **Bandingkan dengan rawak**: setiap hit rate dibaca bersama jangkaan rawak dan p-value.
- **Walk-forward**: penilaian hanya menggunakan maklumat yang tersedia sebelum sesuatu draw.
- **Tiada data leakage**: keputusan masa hadapan tidak digunakan untuk membina pilihan draw terdahulu.
- **Satu keputusan tidak cukup**: keputusan yang kelihatan signifikan mesti diulang pada tempoh data lain, dan p-value dilaraskan apabila banyak strategi diuji.
- **Ringkas dahulu**: engine baharu mesti memberi nilai tambah yang jelas sebelum dimasukkan ke app.
- **Boleh diaudit**: output penting mempunyai sumber dan laluan yang boleh diperiksa.

## Status projek

Projek sedang dibangunkan secara aktif. Selection Engine, Bridge Pair Shortlist dan Bridge Dua Pair tidak lagi dipaparkan; fungsinya digantikan oleh jadual ranking pair dengan pilihan pair dan had nombor. Kod lama yang tidak digunakan (halaman menu yang tidak boleh dicapai, blok `if False`, teks kod tersembunyi, fungsi tanpa rujukan) telah dibuang; lihat `CHANGELOG.md`. Engine keluarga, AI Pick dan ranking legasi tidak menjadi sebahagian daripada aliran aktif.

## Nota penggunaan

Rumah A Predictor ialah alat analisis eksperimen. Cabutan sebenar adalah rawak dan ujian dalam projek ini tidak menunjukkan sebarang enjin yang mengalahkan peluang rawak. Output ialah susunan berdasarkan formula dan sejarah; ia bukan jaminan keputusan atau nasihat kewangan. Sebarang tindakan berdasarkan output adalah tanggungjawab pengguna sendiri.
