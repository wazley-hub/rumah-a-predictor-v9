# Changelog

Semua perubahan penting pada Rumah A Predictor dicatat di sini, yang terbaru di atas.

## V32.4 - 2026-10-30

Kemasan tab dan kotak pilihan. Nombor versi ini cadangan sahaja.

### Diubah

- **CSS tab ditulis semula menggunakan peranan ARIA** (`[role="tab"]`, `[role="tablist"]`) dan bukan `button[data-baseweb="tab"]`. Streamlit 2026 sedang bertukar daripada BaseWeb kepada komponen baharu, jadi selektor lama tidak lagi sepadan dan tab nampak rapat, tanpa padding dan dengan garis merah lalai.
- Tab lebih lapang: jarak 8px, padding 18px, tinggi 42px, pilihan berbentuk pil putih. Garis bawah merah dan garisan kelabu disembunyikan. Pada telefon tab disusun dua baris supaya semua kelihatan.
- **`.streamlit/config.toml` ditulis semula menggunakan pilihan tema rasmi**: `primaryColor`, `secondaryBackgroundColor` putih, `borderColor` dan `showWidgetBorder = true` (sempadan jelas pada kotak pilihan dan input), `baseRadius`, `buttonRadius`, `linkColor`, `codeBackgroundColor`, dan `font` dengan URL Google Fonts. Pilihan ini tidak bergantung pada struktur HTML dalaman Streamlit.

### Ditambah

- Versi Streamlit dipaparkan dalam Alat & Data > Ujian & Backtest untuk membantu diagnosis paparan.
- Ujian bagi CSS (kurungan seimbang, tab guna peranan ARIA) dan bagi `config.toml` (sah, dan selaras dengan token warna).

### Nota

- Jika tab berwarna merah dan kotak pilihan kelabu muncul selepas deploy, `config.toml` tidak dibaca. Semak ia berada di `.streamlit/config.toml` pada akar repositori, kemudian Reboot app.

## V32.3 - 2026-10-30

Warna dan kebolehbacaan. Nombor versi ini cadangan sahaja.

### Diubah

- **Palet dibaiki mengikut ukuran kontras.** Nota kecil sebelum ini 4.35:1, tab tidak aktif 4.27:1, manakala kotak pilihan dan kotak nombor hanya 1.02:1 dan 1.04:1 berbanding latar, jadi nampak kabur dan memenatkan mata. Kini semua teks sekurang-kurangnya 4.5:1 dan sempadan kotak pilihan sekurang-kurangnya 3:1.
- Latar `#F1F4F9`, teks `#0B1530`, teks kedua `#3F4E6B`, biru `#0F4BC4`; `.streamlit/config.toml` dikemas kini sama.
- **Kotak pilihan dan input** kini putih dengan sempadan jelas dan fokus biru, bukan kelabu pucat atas latar pucat.
- **Nota (caption)** tidak lagi dipudarkan oleh opacity Streamlit; label widget lebih tebal dan gelap.
- Teks kedua pada kad utama, kad asal nombor dan jubin signal diperbesarkan dan dipekatkan.

### Ditambah

- **Cip nombor** menggantikan kotak kod untuk Top-N route, pair V1 dan V2, pair enjin 2D dan Match Engine: nombor besar, 3 teratas digelapkan, dengan butang Salin.
- Ujian kontras warna (WCAG AA) dalam `test_ui_theme.py`.
- Ujian asap kini menandakan ralat yang ditangkap dalam blok `try/except`, yang sebelum ini tersembunyi sebagai amaran.

### Dibetulkan

- Dua pepijat ditemui semasa kerja ini sebelum sampai kepada awak: import `re` tiada, dan kunci pemilih pair yang tertukar dalam satu fungsi. Kedua-duanya hanya akan muncul sebagai amaran "belum dapat dipaparkan".

## V32.2 - 2026-10-29

Kemasan UI selepas ujian paparan sebenar. Nombor versi ini cadangan sahaja.

### Ditambah

- **Tab Match Engine** di sebelah Route: jadual ringkas Quattro, Triple, Double dan Bridge Solo (bilangan V1 dan V2), pilihan tahap dan had nombor, dan nombor boleh disalin terus. Tahap yang dipilih signal dibuka secara lalai.
- Pembantu `render_pair_groups`: satu jadual pair dan satu pemilih pair dengan nombor disusun ikut peluang box dan kekerapan terkini.

### Diubah

- Tab utama kini: Route | Match | Bridge V1 | Bridge V2 | Lanjutan (label dipendekkan supaya muat pada telefon).
- **Tab Lanjutan**: enam senarai expander (satu bagi setiap pair) dalam enjin 1st, 2nd dan 3rd 2D diganti dengan jadual pair dan pemilih pair, gaya sama seperti Bridge V1 dan V2. Expander pada halaman turun daripada 57 kepada 14.
- **CSS tab** ditulis semula tanpa bergantung pada nama kelas Streamlit (`.stTabs`), dengan `!important`, supaya sudut tab sentiasa bulat dalam pelbagai versi Streamlit. Berlaku untuk tab utama dan tab Alat & Data.
- Tab tidak lagi berbalut baris, boleh skrol mendatar pada skrin sempit, dan padding dikecilkan pada telefon.

### Dibuang

- Panel Match Engine yang berupa empat expander dan teks panjang dalam tab Route.

## V32.1 - 2026-10-28

Tema visual baharu. Nombor versi ini cadangan sahaja.

### Ditambah

- **`ui_theme.py`**: tema satu fail dengan gaya aplikasi mudah alih kewangan Malaysia: latar `#ECF0F8`, kad putih bersudut bulat, fon Plus Jakarta Sans, nombor besar berlebar tetap.
- **Kad keputusan terkini** berwarna biru tua dengan 1st (kuning), 2nd dan 3rd, tarikh dalam bentuk "25 Okt 2026" dan status sambungan GitHub dan sumber data.
- **Kad "Nombor terkini naik daripada mana"** dengan cip hijau bagi setiap engine yang menjana, cip kelabu bagi nombor tanpa engine, dan senarai laluan dipendekkan (3 pertama, "+N lagi").
- **Jubin Ringkasan Signal** bagi 1st, 2nd dan 3rd: V1 atau V2, jenis (Missing atau Pair), dan sokongan 0 hingga 4 dalam bentuk bar.
- `.streamlit/config.toml` untuk tema cerah, supaya komponen Streamlit tidak bertukar gelap pada mod gelap peranti.
- `test_ui_theme.py`.

### Diubah

- Tab berbentuk pil, butang Generate penuh lebar, input nombor berpusat dengan huruf besar berjarak, jadual dan kod bersudut bulat, butang salin dalam warna biru yang sama.
- Lebar kandungan dihadkan kepada 960px supaya selesa di telefon dan komputer.
- Menu, pautan tajuk dan pengaki "Made with Streamlit" disembunyikan.

### Dibuang

- Lima blok CSS lama yang bertindan (V20, V31.37 dan lain-lain), hero lama dan baris status lama. Kira-kira 300 baris dalam `app.py`; saiznya kini 4,797 baris.
- Panel "Keputusan Terbaru" lama (kini dalam kad utama).

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
