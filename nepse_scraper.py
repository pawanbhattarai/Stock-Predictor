import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
import os
import time

def scrape_merolagani_data(symbol):
    url = f"https://merolagani.com/CompanyDetail.aspx?symbol={symbol}#0"

    # Setup ChromeDriver using the Service class with headless options
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode
    chrome_options.add_argument("--disable-gpu")  # Disable GPU for better performance in headless mode
    chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get(url)
    wait = WebDriverWait(driver, 20)

    try:
        price_history_tab = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_CompanyDetail1_lnkHistoryTab")))
        driver.execute_script("arguments[0].click();", price_history_tab)
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", price_history_tab)

    time.sleep(3)
    all_data = []

    while True:
        try:
            table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table.table.table-bordered.table-striped.table-hover')))
            driver.execute_script("arguments[0].scrollIntoView(true);", table)
            rows = table.find_elements(By.TAG_NAME, 'tr')[1:]  # Skip header row

            if not rows:
                print("No rows found on page.")
                break

            for row in rows:
                cols = row.find_elements(By.TAG_NAME, 'td')
                if len(cols) > 2:  # Assuming Date is in the 1st column and LTP in the 3rd column
                    date = cols[1].text.strip()
                    ltp = cols[2].text.strip()
                    print(f"Date: {date}, LTP: {ltp}")  # Debugging output
                    all_data.append([date, ltp])

        except (NoSuchElementException, StaleElementReferenceException) as e:
            print(f"Error locating elements: {e}. Retrying...")
            continue
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break

        try:
            next_button = wait.until(EC.presence_of_element_located((By.XPATH, "//a[@title='Next Page']")))
            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            
            if 'disabled' in next_button.get_attribute('class'):
                print("Next button is disabled. Exiting.")
                break
            
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(3)
        except (NoSuchElementException, StaleElementReferenceException) as e:
            print(f"Error with next button: {e}. Retrying...")
            continue
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break

    driver.quit()

    print("Total rows of data:", len(all_data))
    
    if not all_data:
        print("No data found. Returning empty DataFrame.")
        return pd.DataFrame()

    # Create DataFrame with Date and LTP
    df = pd.DataFrame(all_data, columns=['Date', 'LTP'])
    
    # Convert 'Date' to datetime format and 'LTP' to float
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['LTP'] = df['LTP'].apply(safe_float)
    
    save_directory = "static/data/"
    csv_file = os.path.join(save_directory, f"{symbol}_stock_data.csv")
    df.to_csv(csv_file, index=False)
    return df

def safe_float(value):
    try:
        return float(value.replace(',', ''))
    except ValueError:
        return None
