import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
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

def scrape_job_data(driver):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])

    url = 'https://pacificaerospaceconsulting.com.au/careers/job-opportunities/'
    driver.get(url)
    print(f"Scraping {url}")
    
    # Wait for page to load
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'lxml')
    
    # Find all job links based on the new structure
    job_boxes = soup.find_all('a', class_='elementor-element', href=True)

    if not job_boxes:
        print("No jobs found on the page.")
        return df

    for box in job_boxes:
        try:
            link = box.get('href')
            
            # Find the job title within the job box
            title_element = box.find('h3', class_='elementor-heading-title')
            job_title = title_element.text.strip() if title_element else 'No Title Found'
            
            # Set default values
            company = 'PAC Aero'
            job_classification = 'N/A'
            location = 'Various'

            new_data = pd.DataFrame({
                'Link': [link],
                'Job Title': [job_title],
                'Job Classification': [job_classification],
                'Location': [location],
                'Company': [company]
            })

            df = pd.concat([df, new_data], ignore_index=True)
            print(f"Found job: {job_title}")

        except Exception as e:
            print(f"Error scraping job: {e}")

    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'PAC_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

# Main execution
if __name__ == "__main__":
    output_dir = '.\\csv_files'
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver)
        if not df.empty:
            save_df_to_csv(df, output_dir)
            print(f"Found {len(df)} jobs")
        else:
            print("No jobs were found to save")
    finally:
        driver.quit()