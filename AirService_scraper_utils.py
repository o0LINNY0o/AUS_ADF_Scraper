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

def scrape_job_data(driver, Job_Classification, location):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])

    url = 'https://careers.airservicesaustralia.com/caw/en/listing/'
    driver.get(url)
    print(f"Scraping {url}")

    soup = BeautifulSoup(driver.page_source, 'lxml')
    # Find the tbody containing job listings
    job_tbody = soup.find('tbody', {'id': 'recent-jobs-content'})
    
    if not job_tbody:
        print("No jobs found")
        return df

    # Process job rows in pairs (job details row and summary row)
    job_rows = job_tbody.find_all('tr')
    
    for i in range(0, len(job_rows), 2):  # Step by 2 to process pairs of rows
        try:
            job_row = job_rows[i]
            
            # Extract job details
            job_link = job_row.find('a', {'class': 'job-link'})
            if not job_link:
                continue
                
            link_full = 'https://careers.airservicesaustralia.com' + job_link['href']
            job_title = job_link.text.strip()
            location = job_row.find('span', {'class': 'location'}).text.strip()
            company = 'AirService'

            print(f"Scraped job: {job_title} - {location}")
            
            new_data = pd.DataFrame({
                'Link': [link_full],
                'Job Title': [job_title],
                'Job Classification': ['N/A'],
                'Location': [location],
                'Company': [company]
            })

            df = pd.concat([df, new_data], ignore_index=True)

        except Exception as e:
            print(f"Error scraping job: {e}")

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
    file_path = os.path.join(output_dir, 'AirService_job_data.csv')

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