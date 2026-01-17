import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

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
   
    url = 'https://epdj.fa.ap1.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/requisitions?location=Australia&locationId=300000000392483&locationLevel=country&mode=job-location'
    driver.get(url)
    print(f"Scraping {url}")

    while True:
        try:
            # Wait for the job listings to load
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "job-list-item")))
            
            # Get all job listings
            job_listings = driver.find_elements(By.CLASS_NAME, "job-list-item")
            
            if not job_listings:
                print("No job listings found on this page.")
                break
            
            for job in job_listings:
                try:
                    link_element = job.find_element(By.CLASS_NAME, "job-list-item__link")
                    link = link_element.get_attribute('href')
                    
                    job_title_element = job.find_element(By.CLASS_NAME, "job-tile__title")
                    job_title = job_title_element.text.strip() if job_title_element else 'N/A'
                    
                    job_info_elements = job.find_elements(By.CLASS_NAME, "job-tile__info")
                    job_classification = job_info_elements[0].text.strip() if len(job_info_elements) > 0 else 'N/A'
                    # Find the location element
                    location_element = job.find_element(By.CSS_SELECTOR, "span[data-bind='html: primaryLocation']")
                    location = location_element.text.strip() if location_element else 'N/A'
                    
                    company = 'NOVA'  # Assuming the company is NOVA for all listings
                    
                    new_data = pd.DataFrame({
                        'Link': [link], 
                        'Job Title': [job_title], 
                        'Job Classification': [job_classification],
                        'Location': [location], 
                        'Company': [company]
                    })

                    df = pd.concat([df, new_data], ignore_index=True)
                    
                except Exception as e:
                    print(f"Error scraping job: {e}")

            # Check for next page
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.search-results__pager-next:not([disabled])"))
                )
                driver.execute_script("arguments[0].click();", next_button)
                WebDriverWait(driver, 20).until(EC.staleness_of(job_listings[0]))
            except TimeoutException:
                print("No more pages to scrape or next button not clickable. Stopping.")
                break
            
        except Exception as e:
            print(f"Error on page: {e}")
            break

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
    file_path = os.path.join(output_dir, 'NOVA_job_data.csv')

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
