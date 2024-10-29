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
    base_url = 'https://careers.l3harris.com'
    url = f'{base_url}/en/location/australia-jobs/4832/2077456/2'
    driver.get(url)
    print(f"Scraping {url}")
    
    page = 1
    while True:
        # Add a small delay to ensure the page loads completely
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'lxml')
        # Find all job listings within the search-results-list
        job_listings = soup.select('#search-results-list ul li')

        if not job_listings:
            print("No jobs found on this page")
            break

        print(f"Processing page {page}")
        for job in job_listings:
            try:
                # Extract job link
                link_element = job.find('a')
                if link_element:
                    link = base_url + link_element.get('href')
                else:
                    continue

                # Extract job title
                job_title_element = job.find('h2')
                job_title = job_title_element.text.strip() if job_title_element else 'No Title'

                # Extract job classification
                job_class_element = job.find('span', {'class': 'results-facet job-category'})
                job_classification = job_class_element.text.strip() if job_class_element else 'Not Specified'

                # Extract location
                location_element = job.find('span', {'class': 'results-facet job-location test3'})
                job_location = location_element.text.strip() if location_element else 'No Location'

                new_data = pd.DataFrame({
                    'Link': [link],
                    'Job Title': [job_title],
                    'Job Classification': [job_classification],
                    'Location': [job_location],
                    'Company': ['L3Harris']
                })

                df = pd.concat([df, new_data], ignore_index=True)
                print(f"Scraped: {job_title} - {job_location}")

            except Exception as e:
                print(f"Error scraping job: {e}")

        # Check for next page using the specific pagination element
        try:
            # Look for the pagination div and next link
            pagination = soup.find('div', {'class': 'pagination-paging paging-right'})
            if not pagination:
                print("No pagination found")
                break
                
            next_link = pagination.find('a', {'class': 'next'})
            
            # Check if next link exists and is not disabled
            if not next_link or 'disabled' in next_link.get('class', []):
                print("Reached last page")
                break
                
            next_url = base_url + next_link['href']
            print(f"Moving to page {page + 1}")
            driver.get(next_url)
            page += 1
            
        except Exception as e:
            print(f"Error finding next page: {e}")
            break

    print(f"Finished scraping. Total pages processed: {page}")
    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    file_path = os.path.join(output_dir, 'L3Harris_job_data.csv')
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