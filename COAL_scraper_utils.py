import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
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
    base_url = 'https://clientapps.jobadder.com/12102/goal-group'
    url = f'{base_url}/12102/goal-group'
    driver.get(url)
    print(f"Scraping {url}")
    
    # Add a small delay to ensure the page loads completely
    time.sleep(2)
    
    soup = BeautifulSoup(driver.page_source, 'lxml')
    # Find all job listings
    job_listings = soup.find_all('div', {'class': 'pricing-item price_item2'})

    if not job_listings:
        print("No jobs found on the page")
        return df

    print("Processing jobs...")
    for job in job_listings:
        try:
            # Extract job link and title
            link_element = job.find('a', {'class': 'viewjob'})
            if link_element:
                link = base_url + link_element.get('href')
                job_title = link_element.text.strip()
            else:
                continue

            # Extract all list items
            list_items = job.find_all('li')
            
            # Get job classification (first list item) and location (third list item)
            job_classification = list_items[0].text.strip() if len(list_items) >= 1 else 'Not Specified'
            job_location = list_items[2].text.strip() if len(list_items) >= 3 else 'Not Specified'

            new_data = pd.DataFrame({
                'Link': [link],
                'Job Title': [job_title],
                'Job Classification': [job_classification],
                'Location': [job_location],
                'Company': ['Coal Group']
            })

            df = pd.concat([df, new_data], ignore_index=True)
            print(f"Scraped: {job_title} - {job_location}")

        except Exception as e:
            print(f"Error scraping job: {e}")

    print(f"Finished scraping. Total jobs found: {len(df)}")
    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    file_path = os.path.join(output_dir, 'CoalGroup_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

# Create the output directory
output_dir = '.\\csv_files'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

if __name__ == "__main__":
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver, 'Engineering', 'Australia')
        save_df_to_csv(df, output_dir)
    finally:
        driver.quit()