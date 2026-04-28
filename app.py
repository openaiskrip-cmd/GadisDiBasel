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
                # --- MODIFIKASI DI SINI ---
                # Mencoba memaksa ke versi 147 sesuai kebutuhan server saat ini
                try:
                    driver = uc.Chrome(options=options, use_subprocess=True, version_main=147)
                except Exception:
                    # Jika gagal (misal server update Chrome), biarkan dia deteksi otomatis
                    driver = uc.Chrome(options=options, use_subprocess=True)
                # --------------------------

                wait = WebDriverWait(driver, 20)
                
                url = f"https://www.google.com/maps/search/{keyword_input.replace(' ','+')}"
                driver.get(url)
                time.sleep(5)

                scroll_habis(driver, wait)
                cards = driver.find_elements(By.CLASS_NAME, "hfpxzc")
                total_found = len(cards)
                
                st.info(f"Ditemukan {total_found} tempat. Memulai pengambilan detail...")
                
                main_tab = driver.current_window_handle
                
                # Progres bar biar user tidak bosan
                my_bar = st.progress(0)
                
                for i in range(min(total_found, 50)): 
                    try:
                        my_bar.progress((i + 1) / min(total_found, 50))
                        
                        cards = driver.find_elements(By.CLASS_NAME, "hfpxzc")
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

                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)
                    
                    st.download_button(
                        label="📥 Download Excel",
                        data=output.getvalue(),
                        file_name=f"hasil_scrape_{int(time.time())}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.error("Tidak ada data yang berhasil diambil.")

                driver.quit()

            except Exception as e:
                st.error(f"Terjadi kesalahan teknis: {e}")
