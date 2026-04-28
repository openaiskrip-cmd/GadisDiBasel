import streamlit as st
import pandas as pd
import time, re, io, sys

try:
    import distutils.version
except:
    pass

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

st.set_page_config(page_title="Maps Scraper")
st.title("📍 Google Maps Scraper")

keyword = st.text_input("Keyword", "cell di bangka selatan")
limit = st.number_input("Limit Data", 1, 100, 30)

# ==================================================
# DRIVER
# ==================================================
def buat_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    return uc.Chrome(
        options=options,
        version_main=147,
        use_subprocess=True
    )

# ==================================================
# HELPER
# ==================================================
def safe_text(driver, by, selector):
    try:
        return driver.find_element(by, selector).text.strip()
    except:
        return "N/A"

def tunggu_nama(driver):
    for _ in range(15):
        try:
            el = driver.find_element(By.XPATH, "//h1")
            txt = el.text.strip()
            if txt:
                return txt
        except:
            pass
        time.sleep(1)
    return "N/A"

def get_latlng(driver):
    url = driver.current_url
    m = re.search(r'@([-0-9\.]+),([-0-9\.]+)', url)
    if m:
        return m.group(1), m.group(2)
    return "N/A","N/A"

def scroll_habis(driver):
    panel = driver.find_element(By.XPATH, '//div[@role="feed"]')

    last = 0
    stuck = 0

    while True:
        driver.execute_script(
            "arguments[0].scrollTop=arguments[0].scrollHeight", panel
        )
        time.sleep(2)

        cards = driver.find_elements(By.CLASS_NAME,"hfpxzc")
        total = len(cards)

        if total > last:
            last = total
            stuck = 0
        else:
            stuck += 1

        if stuck >= 5:
            break

# ==================================================
# MAIN
# ==================================================
if st.button("🚀 Mulai"):
    driver = buat_driver()
    wait = WebDriverWait(driver,20)

    hasil = []

    try:
        url = f"https://www.google.com/maps/search/{keyword.replace(' ','+')}"
        driver.get(url)
        time.sleep(5)

        scroll_habis(driver)

        cards = driver.find_elements(By.CLASS_NAME,"hfpxzc")
        total = min(len(cards), limit)

        bar = st.progress(0)

        main = driver.current_window_handle

        for i in range(total):
            cards = driver.find_elements(By.CLASS_NAME,"hfpxzc")
            href = cards[i].get_attribute("href")

            driver.execute_script("window.open(arguments[0]);", href)
            driver.switch_to.window(driver.window_handles[-1])

            time.sleep(3)

            nama = tunggu_nama(driver)
            alamat = safe_text(driver, By.CSS_SELECTOR,'[data-item-id="address"]')
            telp = safe_text(driver, By.XPATH,'//button[contains(@data-item-id,"phone:tel")]')
            lat,lng = get_latlng(driver)

            hasil.append({
                "Nama": nama,
                "Alamat": alamat,
                "Telepon": telp,
                "Latitude": lat,
                "Longitude": lng
            })

            driver.close()
            driver.switch_to.window(main)

            bar.progress((i+1)/total)

        df = pd.DataFrame(hasil)
        st.dataframe(df)

        output = io.BytesIO()
        df.to_excel(output,index=False)

        st.download_button(
            "📥 Download Excel",
            output.getvalue(),
            "hasil.xlsx"
        )

    finally:
        driver.quit()
