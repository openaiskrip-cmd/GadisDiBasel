import sys
import time
import re
import io
import pandas as pd
import streamlit as st

# =====================================================
# FIX PYTHON 3.12+
# =====================================================
try:
    import distutils.version
except:
    pass

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =====================================================
# PAGE
# =====================================================
st.set_page_config(page_title="Google Maps Scraper", layout="wide")
st.title("📍 Google Maps Scraper Bangka Selatan")

keyword = st.text_input(
    "Masukkan Kata Kunci:",
    value="cell di bangka selatan"
)

# =====================================================
# DRIVER
# =====================================================
def buat_driver():
    options = uc.ChromeOptions()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = uc.Chrome(
        options=options,
        version_main=147,
        use_subprocess=True
    )

    return driver

# =====================================================
# HELPER
# =====================================================
def safe_text(driver, by, selector):
    try:
        return driver.find_element(by, selector).text.strip()
    except:
        return "N/A"


def tunggu_nama(driver):
    kandidat = [
        '//h1',
        '//h1[contains(@class,"DUwDvf")]',
        '//div[@role="main"]//h1'
    ]

    for _ in range(15):
        for xp in kandidat:
            try:
                txt = driver.find_element(
                    By.XPATH, xp
                ).text.strip()

                if txt:
                    return txt
            except:
                pass

        time.sleep(1)

    return "N/A"


def get_latlng(driver):
    url = driver.current_url
    html = driver.page_source

    m1 = re.search(
        r'@([-0-9\.]+),([-0-9\.]+)',
        url
    )

    if m1:
        return m1.group(1), m1.group(2)

    m2 = re.search(
        r'!3d([-0-9\.]+)!4d([-0-9\.]+)',
        html
    )

    if m2:
        return m2.group(1), m2.group(2)

    return "N/A", "N/A"


# =====================================================
# SCROLL
# =====================================================
def scroll_habis(driver, info_box):
    panel_xpath = '//div[@role="feed"]'

    wait = WebDriverWait(driver, 20)

    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, panel_xpath)
        )
    )

    panel = driver.find_element(
        By.XPATH, panel_xpath
    )

    last_total = 0
    stuck = 0
    mulai = time.time()

    while True:

        driver.execute_script("""
            arguments[0].scrollTop =
            arguments[0].scrollHeight
        """, panel)

        time.sleep(2)

        cards = driver.find_elements(
            By.CLASS_NAME,
            "hfpxzc"
        )

        total = len(cards)

        info_box.info(
            f"📌 Menemukan {total} tempat..."
        )

        if total > last_total:
            last_total = total
            stuck = 0
        else:
            stuck += 1

        page = driver.page_source.lower()

        if (
            "akhir daftar" in page or
            "reached the end" in page
        ):
            break

        if stuck >= 5:
            break

        if time.time() - mulai > 300:
            break


# =====================================================
# MAIN
# =====================================================
if st.button("🚀 MULAI SCRAPE"):

    if not keyword:
        st.warning("Masukkan keyword dulu")
        st.stop()

    hasil = []

    status = st.empty()
    progress = st.progress(0)

    try:
        driver = buat_driver()

        status.info("🌍 Membuka Google Maps...")

        url = f"https://www.google.com/maps/search/{keyword.replace(' ','+')}"
        driver.get(url)

        time.sleep(5)

        scroll_habis(driver, status)

        cards = driver.find_elements(
            By.CLASS_NAME,
            "hfpxzc"
        )

        links = []

        for c in cards:
            try:
                href = c.get_attribute("href")
                if href:
                    links.append(href)
            except:
                pass

        total = len(links)

        st.success(
            f"🔥 Total ditemukan {total} tempat"
        )

        # =========================================
        # LOOP SATU TAB (ANTI INVALID SESSION)
        # =========================================
        for i, href in enumerate(links):

            try:
                status.info(
                    f"📥 Mengambil data {i+1} / {total}"
                )

                progress.progress(
                    (i + 1) / total
                )

                driver.get(href)

                time.sleep(3)

                nama = tunggu_nama(driver)

                alamat = safe_text(
                    driver,
                    By.CSS_SELECTOR,
                    '[data-item-id="address"]'
                )

                telp = safe_text(
                    driver,
                    By.XPATH,
                    '//button[contains(@data-item-id,"phone:tel")]'
                )

                lat, lng = get_latlng(driver)

                hasil.append({
                    "Nama": nama,
                    "Alamat": alamat,
                    "Telepon": telp,
                    "Latitude": lat,
                    "Longitude": lng
                })

            except Exception as e:
                continue

        # =========================================
        # HASIL
        # =========================================
        status.success("🎉 Scraping selesai!")

        df = pd.DataFrame(hasil)

        st.dataframe(
            df,
            use_container_width=True
        )

        output = io.BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:
            df.to_excel(
                writer,
                index=False
            )
        nama_file = re.sub(
            r'[^a-zA-Z0-9_ ]',
            '',
            keyword
        ).strip().replace(" ", "_")
        
        if not nama_file:
            nama_file = "hasil_maps"
        
        nama_file = f"{nama_file}_{int(time.time())}.xlsx"
        
        st.download_button(
            label="📥 Download Excel",
            data=output.getvalue(),
            file_name=nama_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        # st.download_button(
        #     label="📥 Download Excel",
        #     data=output.getvalue(),
        #     file_name=f"hasil_{int(time.time())}.xlsx",
        #     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        # )

    except Exception as e:
        st.error(f"Error: {e}")

    finally:
        try:
            driver.quit()
        except:
            pass
