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

def scrape_job_data(driver, Job_Classification, location):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])
   
    url = 'https://careers.au.baesystems.com/jobtools/jncustomsearch.searchResults?in_organid=16804&in_jobDate=All'
    driver.get(url)
    print(f"Scraping {url}")

    while True:
        soup = BeautifulSoup(driver.page_source, 'lxml')
        job_rows = soup.select('tbody > tr')
        
        print(f"Found {len(job_rows)} job rows")
        
        if not job_rows:
            print("No jobs found. Stopping.")
            break
            
        for row in job_rows:
            try:
                columns = row.find_all('td')
                if len(columns) != 4:
                    continue  # Skip rows that don't have the expected number of columns

                link_element = columns[0].find('a')
                if not link_element:
                    continue

                link = link_element.get('href')
                link_full = 'https://careers.au.baesystems.com/jobtools/' + link
                
                job_title = link_element.text.strip()
                
                company = 'BAE'
                                               
                job_classification = columns[1].text.strip()
                
                location = columns[3].text.strip()
                print(f"Scraped job: {job_title} - {location}")

                new_data = pd.DataFrame({
                    'Link': [link_full], 
                    'Job Title': [job_title], 
                    'Job Classification': [job_classification],
                    'Location': [location], 
                    'Company': [company] })

                df = pd.concat([df, new_data], ignore_index=True)
                
            except Exception as e:
                print(f"Error scraping job: {e}")

        try:
            load_more_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'load-more'))
            )
            if 'disabled' in load_more_button.get_attribute('class'):
                #print("Load More button is disabled. Stopping.")
                break
            driver.execute_script("arguments[0].click();", load_more_button)
            #rint("Clicked 'Load More'")
            time.sleep(2)  # Wait for new content to load
        except (NoSuchElementException, TimeoutException):
            #print("No more jobs to scrape. Stopping.")
            break

    return df

output_dir = '.\\csv_files'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'BAE_job_data.csv')

    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

if __name__ == "__main__":
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver, 'Engineering', 'Australia')
        save_df_to_csv(df, output_dir)
    finally:
        driver.quit()