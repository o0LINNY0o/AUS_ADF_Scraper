import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time

def configure_webdriver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument('--log-level=1')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )
    return driver

def handle_cookies(driver):
    try:
        first_cookie_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.cm__btn[data-role='all']"))
        )
        first_cookie_button.click()
        time.sleep(0.5)
    except TimeoutException:
        print("First cookie button not found or not clickable")

    try:
        second_cookie_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        second_cookie_button.click()
        time.sleep(0.5)
    except TimeoutException:
        print("Second cookie button not found or not clickable")

def is_button_visible(driver):
    try:
        button = driver.find_element(By.ID, "load-more")
        return button.is_displayed()
    except (NoSuchElementException, StaleElementReferenceException):
        return False

def click_load_more(driver):
    try:
        load_more_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "load-more"))
        )
        
        driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
        time.sleep(0.5)        
        driver.execute_script("arguments[0].click();", load_more_button)             
        time.sleep(1)
        return True
    except (TimeoutException, StaleElementReferenceException) as e:
        print(f"Error clicking Load More button: {e}")
        return False

def load_all_jobs(driver):
    print("Loading all jobs...")
    click_count = 0
    while True:
        if is_button_visible(driver):
            if click_load_more(driver):
                click_count += 1                
            else:
                break
        else:            
            break    

def scrape_job_data(driver):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Category', 'Location', 'Company'])
    
    url = 'https://careers.airbusgroupap.com.au/jobtools/jncustomsearch.searchResults?in_organid=17272&in_jobDate=All&in_sessionid='
    print(f"Scraping {url}")

    driver.get(url)
    handle_cookies(driver)
    time.sleep(2)
    
    load_all_jobs(driver)
    
    try:
        print("Processing all loaded jobs...")
        soup = BeautifulSoup(driver.page_source, 'lxml')
        job_items = soup.select('ul.jobs-list li.job-item')
        
        if not job_items:
            print("No jobs found.")
            return df
        
        total_jobs = len(job_items)        
        
        for index, item in enumerate(job_items, 1):
            try:                
                link_element = item.select_one('h3.load-place a')
                if not link_element:
                    continue
                
                link_full = 'https://careers.airbusgroupap.com.au' + link_element.get('href')
                job_title = link_element.text.strip()                
                
                location_element = item.select_one('p.loc-mark span:last-child')
                location = location_element.text.strip() if location_element else ''                
                
                job_category = ''
                category_element = item.select_one('.row:last-child p:first-child .load-place')
                if category_element:
                    job_category = category_element.text.strip()

                company = 'AIRBUS'
                
                print(f"Scraped job: {job_title} - {location}")

                new_data = pd.DataFrame({
                    'Link': [link_full],
                    'Job Title': [job_title],
                    'Job Category': [job_category],
                    'Location': [location],
                    'Company': [company]
                })

                df = pd.concat([df, new_data], ignore_index=True)
                
            except Exception as e:
                print(f"Error processing job {index}: {e}")

    except Exception as e:
        print(f"Error processing jobs: {e}")

    print(f"Total jobs scraped: {len(df)}")
    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'AIRBUS_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

if __name__ == "__main__":
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver)
        save_df_to_csv(df, '.\\csv_files')
    finally:
        driver.quit()