import streamlit as st
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import pandas as pd
import io

# ==========================================
# 1. SETUP MESIN LOGIKA FUZZY (MAMDANI)
# ==========================================
def setup_fuzzy():
    # Membuat rentang nilai 0 - 60 dengan presisi desimal 0.1
    x1 = ctrl.Antecedent(np.arange(0, 60.1, 0.1), 'multiplier_ekonomi')
    x2 = ctrl.Antecedent(np.arange(0, 60.1, 0.1), 'gaya_hidup_sehat')
    y = ctrl.Consequent(np.arange(0, 60.1, 0.1), 'permintaan_premium')

    # Nama kategori sesuai permintaan
    categories = ['sangat_rendah', 'rendah', 'sedang', 'tinggi', 'sangat_tinggi']

    # Membuat Fungsi Keanggotaan (Kurva Segitiga) berdasarkan batas rentang
    for var in [x1, x2, y]:
        var['sangat_rendah'] = fuzz.trapmf(var.universe, [0, 0, 6, 13])
        var['rendah']        = fuzz.trimf(var.universe, [6, 19, 25])
        var['sedang']        = fuzz.trimf(var.universe, [19, 31, 37])
        var['tinggi']        = fuzz.trimf(var.universe, [31, 43, 49])
        var['sangat_tinggi'] = fuzz.trapmf(var.universe, [43, 49, 60, 60])

    # Membuat 25 Aturan (Rules) secara Otomatis
    # Logika: (Index X1 + Index X2) // 2 = Index Output
    # Contoh: (Rendah[1] + Tinggi[3]) // 2 = Sedang[2]
    rules = []
    for i, cat1 in enumerate(categories):
        for j, cat2 in enumerate(categories):
            out_idx = (i + j) // 2
            out_cat = categories[out_idx]
            rules.append(ctrl.Rule(x1[cat1] & x2[cat2], y[out_cat]))

    # Memasukkan ke sistem kontrol
    system = ctrl.ControlSystem(rules)
    return ctrl.ControlSystemSimulation(system)

# Inisialisasi simulasi
simulasi_fuzzy = setup_fuzzy()

# ==========================================
# 2. FUNGSI PENENTU KATEGORI HASIL (LABELING)
# ==========================================
def tentukan_kategori(nilai):
    if nilai <= 12.99: return "Sangat Rendah"
    elif nilai <= 24.99: return "Rendah"
    elif nilai <= 36.99: return "Sedang"
    elif nilai <= 48.99: return "Tinggi"
    else: return "Sangat Tinggi"

# ==========================================
# 3. ANTARMUKA STREAMLIT (UI)
# ==========================================
st.set_page_config(page_title="Fuzzy Premium Demand", layout="wide")
st.title("Sistem Logika Fuzzy: Prediksi Permintaan Produk Premium")
st.write("Menggunakan metode Mamdani untuk memprediksi Permintaan Produk Premium (Y) berdasarkan Multiplier Ekonomi (X1) dan Gaya Hidup Sehat (X2).")

# Membuat sistem Tab untuk 2 Fitur (Manual & Dataset)
tab1, tab2 = st.tabs(["🎛️ Input Manual", "📁 Input via Dataset"])

# ----------------- TAB 1: MANUAL -----------------
with tab1:
    st.header("Kalkulator Manual")
    col1, col2 = st.columns(2)
    
    with col1:
        val_x1 = st.number_input("Input X1: Multiplier Ekonomi (0 - 60)", min_value=0.0, max_value=60.0, value=20.0, step=0.1)
    with col2:
        val_x2 = st.number_input("Input X2: Gaya Hidup Sehat (0 - 60)", min_value=0.0, max_value=60.0, value=30.0, step=0.1)
        
    if st.button("Hitung Permintaan", type="primary"):
        try:
            # Memasukkan input ke sistem fuzzy
            simulasi_fuzzy.input['multiplier_ekonomi'] = val_x1
            simulasi_fuzzy.input['gaya_hidup_sehat'] = val_x2
            simulasi_fuzzy.compute()
            
            # Mengambil output
            hasil_y = simulasi_fuzzy.output['permintaan_premium']
            kategori_y = tentukan_kategori(hasil_y)
            
            # Menampilkan hasil
            st.success("Berhasil dihitung!")
            st.metric(label="Tingkat Permintaan Produk Premium (Crisp Output)", value=f"{hasil_y:.2f}")
            st.info(f"Kategori Permintaan: **{kategori_y}**")
            
        except Exception as e:
            st.error("Terjadi kesalahan komputasi. Pastikan nilai di dalam rentang 0-60.")

# ----------------- TAB 2: DATASET -----------------
with tab2:
    st.header("Prediksi Massal (Batch Processing)")
    st.write("Unggah file CSV atau Excel Anda. Pastikan memiliki kolom bernama **X1** dan **X2**.")
    
    file_unggahan = st.file_uploader("Pilih file dataset", type=['csv', 'xlsx'])
    
    if file_unggahan is not None:
        # Membaca file
        if file_unggahan.name.endswith('.csv'):
            df = pd.read_csv(file_unggahan)
        else:
            df = pd.read_excel(file_unggahan)
            
        # Validasi nama kolom
        if 'X1' not in df.columns or 'X2' not in df.columns:
            st.error("Format salah! File harus memiliki kolom 'X1' dan 'X2'.")
        else:
            st.write("Pratinjau Data Anda:")
            st.dataframe(df.head())
            
            if st.button("Proses Seluruh Data"):
                hasil_crisp = []
                kategori_list = []
                
                # Proses iterasi per baris
                for index, row in df.iterrows():
                    try:
                        simulasi_fuzzy.input['multiplier_ekonomi'] = float(row['X1'])
                        simulasi_fuzzy.input['gaya_hidup_sehat'] = float(row['X2'])
                        simulasi_fuzzy.compute()
                        
                        nilai_akhir = simulasi_fuzzy.output['permintaan_premium']
                        hasil_crisp.append(round(nilai_akhir, 2))
                        kategori_list.append(tentukan_kategori(nilai_akhir))
                    except:
                        hasil_crisp.append(None)
                        kategori_list.append("Error")
                
                # Menambahkan hasil ke DataFrame
                df['Permintaan_Premium (Y)'] = hasil_crisp
                df['Kategori_Y'] = kategori_list
                
                st.success("Pemrosesan Selesai!")
                st.dataframe(df)
                
                # Fitur Unduh Hasil
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Unduh Hasil (.csv)",
                    data=csv,
                    file_name="hasil_prediksi_premium.csv",
                    mime="text/csv",
                )