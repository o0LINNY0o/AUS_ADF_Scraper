import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
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
    driver = webdriver.Chrome(options=options)
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )
    return driver

def scrape_job_data(driver, Job_Classification, location_filter):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])

    url = 'https://www.anduril.com/open-roles?search=australia'
    driver.get(url)
    print(f"Scraping {url}")
    time.sleep(5)  # Increased wait time for page to fully load

    # Scroll to load all content
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    soup = BeautifulSoup(driver.page_source, 'lxml')
    
    # Updated selectors to match the actual HTML structure
    job_items = soup.select('button.OpenRolesSliceItem.open-roles-item')
    
    print(f"Found {len(job_items)} job listings")

    if not job_items:
        print("No jobs found. Stopping.")
        return df

    for item in job_items:
        try:
            # Find job title
            job_title_element = item.find('div', class_='open-roles-item__title')
            
            # Find location
            location_element = item.find('p', class_='location')
            
            # Find link
            link_element = item.find('a', class_='ExternalLinkButton')

            if not job_title_element or not location_element or not link_element:
                continue

            job_title = job_title_element.text.strip()
            location = location_element.text.strip()
            link = link_element.get('href')

            company = 'Anduril'

            print(f"Scraped job: {job_title} - {location}")

            new_data = pd.DataFrame({
                'Link': [link],
                'Job Title': [job_title],
                'Job Classification': [Job_Classification],
                'Location': [location],
                'Company': [company]
            })

            df = pd.concat([df, new_data], ignore_index=True)

        except Exception as e:
            print(f"Error scraping job: {e}")

    return df

output_dir = '.\\csv_files'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'Anduril_job_data.csv')

    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")
    print(f"Total jobs scraped: {len(df)}")

if __name__ == "__main__":
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver, 'Engineering', 'Australia')
        save_df_to_csv(df, output_dir)
    finally:
        driver.quit()