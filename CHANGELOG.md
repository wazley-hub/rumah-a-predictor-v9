# Changelog

Semua perubahan penting pada Rumah A Predictor dicatat di sini, yang terbaru di atas.

## V32.0 - 2026-10-28

Pembersihan besar, UI baharu, dan ujian terhadap peluang rawak. Nombor versi ini ialah cadangan; ubah mengikut penomboran awak.

### Ditambah

- **`backtest_baseline.py`**: backtest yang membandingkan setiap model dengan peluang rawak (padanan exact dan box), dengan p-value dan p terlaras Bonferroni, serta walk-forward top-K tanpa kebocoran data. Boleh dijalankan sendiri: `python backtest_baseline.py TotoHistoryAll.xlsx --draws 2000 --k 10`.
- **`ranking_engine.py`**: ranking pair Bridge V1 dan V2 yang dinamik (skor = peluang rawak semasa x lift berpemberat susut-masa), susunan nombor dalam pair, shortlist konsensus Top-N, dan diagnostik ranking.
- **`latest_origin.py`**: jadual **"Nombor terkini naik daripada mana"** terus dalam app, menunjukkan engine, laluan dan kedudukan pair yang menjana 1st, 2nd dan 3rd daripada ramalan draw sebelumnya. Tidak perlu muat turun backtest lagi.
- **Panel baharu** dalam Ujian & Backtest: *Backtest vs Rawak (Top-K, walk-forward)* dan *Diagnostik Ranking Pair*.
- **Jadual perbandingan peluang rawak** dalam hasil Backtest Bridge V1 + V2.
- **Ujian automatik**: `smoke_test_app.py` (jalankan app penuh dengan Streamlit palsu; semak ralat, expander bersarang dan widget berganda; `FORCE_BUTTONS` untuk menekan butang Backtest dan Diagnostik), `test_backtest_baseline.py`, `test_ranking_engine.py`, `test_latest_origin.py`.

### Diubah

- **UI**: Keputusan Terbaru, Nombor terkini naik daripada mana, borang Generate, **Ringkasan Signal** di atas, kemudian tab Route Signal | Bridge V1 | Bridge V2 | Lanjutan. Sejarah Keputusan dan Ujian & Backtest dipindahkan ke tab Alat & Data di bawah.
- **Hasil Generate kekal** apabila dropdown ditukar (disimpan dalam sesi), dan menyatakan draw yang digunakan.
- **Pilihan Pair V1 dan V2** kini satu jadual yang disusun daripada skor tertinggi, dikira berasingan bagi V1 dan V2, dengan pilihan pair dan had nombor (Top 10 / 20 / 30 / Semua). Sebelum ini 8 expander dalam urutan tetap (1st Front sentiasa dahulu).
- **Route Signal** mengundi guna lift (hit dibahagi jangkaan liputan), bukan hit rate mentah. Sebelum ini laluan dengan calon lebih banyak menang kerana liputan lebih besar.
- **Top-N Route Terpilih** (5 / 10 / 15 / 20 / 30) dalam Ringkasan Signal.
- **Nama fail muat turun**: `Rumah_A_Predictor_Backtest_Clean_Review_V31_23_3.xlsx` menjadi `Rumah_A_Backtest_Draw<no>_<n>draw.xlsx`; CSV ujian rawak menjadi `Rumah_A_Backtest_vs_Rawak_Top<k>_<n>draw.csv`.
- `requirements.txt` guna julat versi.
- Hujung baris diseragamkan kepada LF.

### Dibuang

- Halaman menu **Analysis, History, Settings dan About** (tidak boleh dicapai kerana menu dikunci pada Home).
- Blok `if False:` dan `False and ...`, serta kod paparan lama yang disimpan sebagai teks tersembunyi (rentetan `_hidden_route_details`, `_consensus_ui_hidden`, `_old_triple_match_hidden`, `_legacy_hidden_ui`).
- Fungsi tanpa rujukan: Selection Engine, Bridge Pair Shortlist, Bridge Dua Pair, ranking pair lama, `build_4_route_signal`, `build_second_prize_2d_carry_engine`, `build_audit_snapshots_fast_v31_29` dan pembantu berkaitan (15 fungsi).
- Pemboleh ubah yang dikira tetapi tidak pernah digunakan, serta import yang tidak digunakan (`product`, `defaultdict`).
- Expander bersarang dalam Route Signal, History Manager dan panel Backtest (tidak dibenarkan Streamlit).
- Saiz `app.py` turun daripada 6,448 kepada 5,103 baris. Paparan dan jadual data sebelum dan selepas pembersihan telah dibandingkan dan sama, termasuk laluan yang memerlukan butang Backtest dan Diagnostik ditekan.

### Dibetulkan

- `@st.cache_data` bertindan pada `build_audit`.
- Hit rate box dalam Backtest Bridge nampak tinggi (51% dan 56%) tetapi sama dengan jangkaan rawak (53% dan 56%); kini dipaparkan bersama jangkaan rawak.

### Keputusan ujian (data sehingga Oktober 2026)

- Tiada enjin yang mengalahkan peluang rawak secara signifikan: Bridge V1 dan V2, strategi top 10 walk-forward 2,000 draw, Route Signal lama dan baru, ranking pair dinamik.
- Top 10 konsensus nampak baik pada 500 draw terakhir (8.7% berbanding jangkaan 6.1%) tetapi tidak berulang pada 1,000 draw sebelumnya (5.1% berbanding 6.2%).
- Ranking pair kini berubah mengikut draw (slot teratas berubah pada 84% draw berbanding 9.8% dahulu), tetapi susunan itu tidak meramal.
