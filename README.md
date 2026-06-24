# Rumah A Predictor V28

Perubahan V28:
- Prediction Audit diringkaskan seperti diminta:
  Draw, Date, Result, AI Pick YES/NO, Model YES/NO, Source, No.
- Buang paparan ramalan panjang daripada Prediction Audit / Past Predictions.
- History Manager dibina semula supaya data ikut Draw No yang dipilih.
- Delete dan Update dipisahkan dalam form yang jelas.
- Formula ramalan tidak diubah.

Nota:
- Streamlit memang akan rerun bila selectbox/radio ditukar. Itu normal.
- Yang dibaiki ialah data tidak lagi patut bercampur dengan draw lain.

Upload/replace:
- app.py
- README.md

Jangan replace:
- TotoHistoryAll.xlsx
