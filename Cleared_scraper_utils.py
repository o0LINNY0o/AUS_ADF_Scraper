import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

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

    url = 'https://www.clearedrecruitment.com.au/jobs/'
    driver.get(url)
    print(f"Scraping {url}")

    page_number = 1
    while True:
        print(f"Scraping page {page_number}")
        soup = BeautifulSoup(driver.page_source, 'lxml')
        job_boxes = soup.find_all('div', {'class': 'main-result-info-panel'})

        if not job_boxes:
            print("No jobs found on current page")
            break

        for box in job_boxes:
            try:
                # Extract job details
                job_details = box.find('div', {'class': 'job-details'})
                
                # Get job title and link
                job_title_element = job_details.find('div', {'class': 'job-title'}).find('a')
                job_title = job_title_element.text.strip()
                link_full = 'https://www.clearedrecruitment.com.au' + job_title_element['href']

                # Get location
                location = job_details.find('li', {'class': 'results-job-location'}).text.strip()

                # Set job classification and company
                job_classification = Job_Classification  # Using the input parameter
                company = 'Cleared Recruitment'

                new_data = pd.DataFrame({
                    'Link': [link_full],
                    'Job Title': [job_title],
                    'Job Classification': [job_classification],
                    'Location': [location],
                    'Company': [company]
                })

                df = pd.concat([df, new_data], ignore_index=True)
                
                print(f"Scraped: {job_title} - {location}")

            except Exception as e:
                print(f"Error scraping job: {e}")

        # Try to find the next page link
        try:
            next_page = soup.find('a', {'rel': 'next'})
            if not next_page:
                print("No more pages to scrape")
                break

            next_url = 'https://www.clearedrecruitment.com.au' + next_page['href']
            driver.get(next_url)
            page_number += 1

        except Exception as e:
            print(f"Error navigating to next page: {e}")
            break

    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'Cleared_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

# Create the output directory
output_dir = '.\\csv_files'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Main execution
if __name__ == "__main__":
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver, 'Engineering', 'Australia')
        save_df_to_csv(df, output_dir)
    finally:
        driver.quit()