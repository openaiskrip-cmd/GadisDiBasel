import sys
import time
import re
import io
import pandas as pd
import streamlit as st

# --- FIX UNTUK PYTHON 3.12+ (Penting untuk versi 3.13.3) ---
try:
    import distutils.version
except ImportError:
    import setuptools
    try:
        from setuptools import distutils
        sys.modules['distutils'] = distutils
    except ImportError:
        pass

# Sekarang baru impor undetected_chromedriver
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    st.error("Library pendukung belum terinstal. Pastikan requirements.txt sudah benar.")

# =====================================================
# KONFIGURASI HALAMAN
# =====================================================
st.set_page_config(page_title="Scraper Bangka Selatan", layout="wide")
st.title("📍 Google Maps Scraper - Bangka Selatan")

# Input di Halaman Utama
keyword_input = st.text_input("Masukkan Kata Kunci:", value="cell di bangka selatan")

# =====================================================
# FUNGSI-FUNGSI PENDUKUNG
# =====================================================

def safe_text(driver, by, selector):
    try:
        return driver.find_element(by, selector).text.strip()
    except:
        return "N/A"

def get_latlng(driver):
    url = driver.current_url
    html = driver.page_source
    m1 = re.search(r'@([-0-9\.]+),([-0-9\.]+)', url)
    if m1: return m1.group(1), m1.group(2)
    m2 = re.search(r'!3d([-0-9\.]+)!4d([-0-9\.]+)', html)
    if m2: return m2.group(1), m2.group(2)
    return "N/A", "N/A"

def scroll_habis(driver, wait):
    panel_xpath = '//div[@role="feed"]'
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, panel_xpath)))
        panel = driver.find_element(By.XPATH, panel_xpath)
        last_total, stuck, mulai = 0, 0, time.time()

        while True:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", panel)
            time.sleep(3)
            cards = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            total = len(cards)
            if total > last_total:
                stuck, last_total = 0, total
            else:
                stuck += 1
            
            page = driver.page_source.lower()
            if any(x in page for x in ["akhir daftar", "reached the end", "telah mencapai"]): break
            if stuck >= 5 or (time.time() - mulai > 300): break
    except:
        pass

# =====================================================
# PROSES UTAMA
# =====================================================

if st.button("🚀 MULAI SCRAPE"):
    if not keyword_input:
        st.warning("Silakan masukkan kata kunci dulu!")
    else:
        with st.spinner(f"Sedang mencari data untuk: {keyword_input}..."):
            hasil = []
            options = uc.ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")

            try:
                # Mencoba versi 147 sesuai error sebelumnya, jika gagal otomatis cari yang lain
                try:
                    driver = uc.Chrome(options=options, use_subprocess=True, version_main=147)
                except:
                    driver = uc.Chrome(options=options, use_subprocess=True)
                
                wait = WebDriverWait(driver, 20)
                
                # Buka Google Maps
                url = f"https://www.google.com/maps/search/{keyword_input.replace(' ','+')}"
                driver.get(url)
                time.sleep(5)

                scroll_habis(driver, wait)
                cards = driver.find_elements(By.CLASS_NAME, "hfpxzc")
                total_found = len(cards)
                
                st.info(f"Ditemukan {total_found} tempat. Memulai pengambilan detail...")
                
                my_bar = st.progress(0)
                main_tab = driver.current_window_handle
                
                # Ambil maksimal 30 data saja agar tidak timeout di server gratisan
                limit = min(total_found, 30)
                
                for i in range(limit):
                    try:
                        my_bar.progress((i + 1) / limit)
                        cards = driver.find_elements(By.CLASS_NAME, "hfpxzc")
                        if i >= len(cards): break
                        
                        href = cards[i].get_attribute("href")
                        if not href: continue

                        driver.execute_script("window.open(arguments[0]);", href)
                        driver.switch_to.window(driver.window_handles[-1])
                        time.sleep(3) 
                        
                        lat, lng = get_latlng(driver)
                        alamat = safe_text(driver, By.CSS_SELECTOR, '[data-item-id="address"]')
                        telp = safe_text(driver, By.XPATH, '//button[contains(@data-item-id,"phone:tel")]')
                        nama = driver.title.split(" - ")[0]

                        hasil.append({
                            "Nama": nama,
                            "Alamat": alamat,
                            "Telepon": telp,
                            "Latitude": lat,
                            "Longitude": lng
                        })
                        
                        driver.close()
                        driver.switch_to.window(main_tab)
                    except:
                        continue

                # Tampilkan Hasil
                if hasil:
                    df = pd.DataFrame(hasil)
                    st.success(f"Berhasil mengambil {len(df)} data!")
                    st.dataframe(df)

                    # Export ke Excel
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)
                    
                    st.download_button(
                        label="📥 Download Excel",
                        data=output.getvalue(),
                        file_name=f"hasil_basel_{int(time.time())}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.error("Tidak ada data yang berhasil diambil.")

                driver.quit()

            except Exception as e:
                st.error(f"Terjadi kesalahan teknis: {e}")
