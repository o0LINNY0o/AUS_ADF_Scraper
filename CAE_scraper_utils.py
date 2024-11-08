import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time
import sys

# Redirect standard error to devnull to suppress Chrome errors
sys.stderr = open(os.devnull, 'w')

def configure_webdriver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument('--log-level=3')  
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
    page = 0
    jobs_per_page = 10

    while True:
        url = f'https://careers.cae.com/global/en/search-results?from={page * jobs_per_page}&s=1&lk=Australia'
        driver.get(url)
        print(f"Scraping page {page + 1}")

        if page == 0:
            # Accept cookies only on first page
            wait = WebDriverWait(driver, 10)
            try:
                button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-accept-btn-handler"]')))
                driver.execute_script("arguments[0].click()", button)
                time.sleep(2)

                # Select Australia by text
                australia_button = wait.until(EC.presence_of_element_located((By.XPATH, '//span[text()="Australia"]')))
                driver.execute_script("arguments[0].scrollIntoView(true);", australia_button)
                driver.execute_script("arguments[0].click();", australia_button)
                time.sleep(2)

            except TimeoutException as e:
                print(f"TimeoutException: {e}")
            except NoSuchElementException as e:
                print(f"NoSuchElementException: {e}")
            except Exception as e:
                print(f"Exception: {e}")

        # Wait for job listings to be present
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'ul[data-ph-at-id="jobs-list"] li.jobs-list-item')))
        except TimeoutException:
            print("No jobs found on current page")
            break

        soup = BeautifulSoup(driver.page_source, 'lxml')
        job_listings = soup.select('ul[data-ph-at-id="jobs-list"] li.jobs-list-item')

        if not job_listings:
            print("No jobs found on current page")
            break

        for job in job_listings:
            try:
                job_link = job.find('a', {'data-ph-at-id': 'job-link'})
                if not job_link:
                    continue

                link_full = job_link.get('href', '')
                job_title = job_link.get('data-ph-at-job-title-text', '')
                location = job_link.get('data-ph-at-job-location-text', 'N/A')
                company = 'CAE'

                new_data = pd.DataFrame({
                    'Link': [link_full],
                    'Job Title': [job_title],
                    'Job Classification': [Job_Classification],
                    'Location': [location],
                    'Company': [company]
                })

                df = pd.concat([df, new_data], ignore_index=True)
                print(f"Scraped: {job_title} - {location}")

            except Exception as e:
                print(f"Error scraping job: {e}")

        # Check for the "View next page" button
        try:
            next_page_button = wait.until(EC.presence_of_element_located((By.XPATH, '//a[@aria-label="View next page"]')))
            driver.execute_script("arguments[0].click();", next_page_button)
            page += 1
            time.sleep(1)
        except TimeoutException:
            print("No more pages to scrape")
            break

    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'CAE_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

# Main execution
if __name__ == "__main__":
    output_dir = '.\\csv_files'
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver, 'Engineering', 'Australia')
        save_df_to_csv(df, output_dir)
    finally:
        driver.quit()
