import os
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

def configure_webdriver():
    """Configure and return an optimized Chrome webdriver."""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--log-level=3')  # Reduce logging
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-logging')
    options.add_argument('--disable-notifications')
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )
    driver.set_page_load_timeout(30)
    return driver

def accept_cookies(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"))
        ).click()
        time.sleep(1)
    except:
        pass  # Continue if no cookie prompt appears

def click_show_more(driver):
    try:
        # Direct selector for the show more button
        button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "btn-outline-blue"))
        )
        
        if "Show" in button.text:
            # Quick scroll and click
            driver.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", button)
            time.sleep(1)  # Minimal wait time
            return True
            
    except:
        return False
    
    return False

def extract_job_info(box):
    try:
        href = box.get('href', '')
        link_full = 'https://www.saab.com' + href if href else ''
        
        title_div = box.find('div', class_='vacancies__item-position')
        job_title = title_div.text.strip() if title_div else ''
        
        regular_items = box.find_all('div', class_='vacancies__item-regular')
        Job_Classification = regular_items[0].text.strip() if regular_items else ''
        location = regular_items[-1].text.strip() if regular_items else ''
        print(f"Scraped job: {job_title} - {location}")
        
        return {
            'Link': link_full,
            'Job Title': job_title,
            'Job Classification': Job_Classification,
            'Location': location,
            'Company': 'Saab'
        }
    
    except Exception as e:
        print(f"Error extracting job info: {e}")
        return None

def scrape_job_data(driver):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])
    job_data = []
    
    # Load the page
    driver.get('https://www.saab.com/markets/australia/careers/job-opportunities')
    accept_cookies(driver)
    
    # Click through all "Show more" buttons
    while click_show_more(driver):
        pass
    
    # Extract all jobs at once
    soup = BeautifulSoup(driver.page_source, 'lxml')
    job_boxes = soup.find_all('a', class_='item vacancy__item-link')
    
    # Process all jobs in a batch
    for box in job_boxes:
        job_info = extract_job_info(box)
        if job_info:
            job_data.append(job_info)
    
    # Create DataFrame in one go
    if job_data:
        df = pd.DataFrame(job_data)
        print(f"Successfully scraped {len(df)} jobs")
    
    return df

def save_df_to_csv(df, output_dir='csv_files'):
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, 'Saab_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"Saved {len(df)} jobs to {file_path}")

def main():
    start_time = time.time()
    driver = None
    
    try:
        driver = configure_webdriver()
        df = scrape_job_data(driver)
        save_df_to_csv(df)
        
        end_time = time.time()
        print(f"Total execution time: {end_time - start_time:.2f} seconds")
        
    except Exception as e:
        print(f"Error during execution: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()