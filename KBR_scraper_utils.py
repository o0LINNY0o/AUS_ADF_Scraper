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

    url = 'https://careers.kbr.com/us/en/search-results?qcountry=Australia'
    driver.get(url)
    print(f"Scraping {url}")

    while True:
        # Wait for the page to load
        driver.implicitly_wait(10)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        
        # Find all job listings
        job_listings = soup.find_all('a', {'data-ph-at-id': 'job-link'})

        if not job_listings:
            print("No jobs found on current page")
            break

        for job in job_listings:
            try:
                # Extract job details using data attributes
                link = job.get('href', '')
                job_title = job.get('data-ph-at-job-title-text', '')
                job_classification = job.get('data-ph-at-job-category-text', '')
                location = job.get('data-ph-at-job-location-text', '')
                
                new_data = pd.DataFrame({
                    'Link': [link],
                    'Job Title': [job_title],
                    'Job Classification': [job_classification],
                    'Location': [location],
                    'Company': ['KBR']
                })

                df = pd.concat([df, new_data], ignore_index=True)

            except Exception as e:
                print(f"Error scraping job: {e}")

        # Check for next page
        next_button = soup.find('a', {'data-ph-at-id': 'pagination-next-link'})
        if not next_button or 'icon-arrow-right' not in str(next_button):
            print("No more pages to scrape")
            break

        next_url = next_button.get('href')
        if not next_url:
            break
            
        print(f"Moving to next page: {next_url}")
        driver.get(next_url)

    return df

# Create the .csv_files directory if it doesn't exist
output_dir = '.\\csv_files'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def save_df_to_csv(df, output_dir):
    # Ensure the directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Define the file path for the CSV
    file_path = os.path.join(output_dir, 'KBR_job_data.csv')

    # Save the DataFrame to a CSV file
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

# Main execution
if __name__ == "__main__":
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver, 'Engineering', 'Australia')
        save_df_to_csv(df, output_dir)
    finally:
        driver.quit()
