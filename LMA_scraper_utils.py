import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

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

def scrape_current_page(soup):
    jobs_data = []
    jobs = soup.find_all('li', class_='job')
    
    for job in jobs:
        try:
            # Extract job title
            job_title_tag = job.find('span', class_='screenReaderText')
            job_title = job_title_tag.text.strip() if job_title_tag else 'N/A'

            # Extract job link
            job_link_tag = job.find('a', class_='jobProperty jobtitle')
            link = job_link_tag['href'] if job_link_tag else 'N/A'

            # Extract job classification and location
            job_details = job.find_all('p', class_='jobProperty position3')
            if len(job_details) >= 2:
                location = job_details[0].text.strip()
                Job_Classification = job_details[1].text.strip()
            else:
                location = 'N/A'
                Job_Classification = 'N/A'
            
            jobs_data.append({
                'Link': link,
                'Job Title': job_title,
                'Job Classification': Job_Classification,
                'Location': location,
                'Company': 'LMA'
            })
            
            print(f"Scraped: {job_title} - {location}")
            
        except Exception as e:
            print(f"Error scraping job: {e}")
    
    return jobs_data

def scrape_job_data(driver):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])
   
    url = 'https://krb-sjobs.brassring.com/TGnewUI/Search/Home/Home?partnerid=30122&siteid=6621#keyWordSearch=&locationSearch=Australia'
    driver.get(url)
    print(f"Scraping {url}")

    # Wait for the page to load and elements to be present
    wait = WebDriverWait(driver, 10)

    # Locate and fill in the location field
    location_field = wait.until(EC.presence_of_element_located((By.ID, 'initialSearchBox__395')))
    location_field.clear()
    location_field.send_keys('Australia')
        
    # Submit the search form
    search_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "primaryButton") and contains(@class, "ladda-button")]')))
    search_button.click()

    # Initial wait for jobs to load
    print("Waiting for initial jobs to load...")
    time.sleep(10)

    page_num = 1
    while True:
        try:
            # Wait for job list to be present
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'ul.jobList')))
            
            print(f"\nScraping page {page_num}...")
            
            # Parse current page
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            current_page_data = scrape_current_page(soup)
            
            # Add current page data to DataFrame
            if current_page_data:
                df = pd.concat([df, pd.DataFrame(current_page_data)], ignore_index=True)
                print(f"Total jobs scraped so far: {len(df)}")
            
            # Check for "Next" button and click if present
            try:
                next_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "showMoreJobs"))
                )
                
                # Check if button is clickable/visible
                if next_button.is_displayed() and next_button.is_enabled():
                    driver.execute_script("arguments[0].click();", next_button)
                    print("Clicked Next button, waiting for new jobs to load...")
                    time.sleep(10)  # Wait for new content to load
                    page_num += 1
                else:
                    print("Next button not clickable - reached last page")
                    break
                    
            except Exception as e:
                print(f"No more pages to scrape: {e}")
                break
                
        except Exception as e:
            print(f"Error during scraping: {e}")
            break

    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'LMA_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"\nData saved to {file_path}")
    print(f"Total jobs scraped: {len(df)}")

# Create output directory
output_dir = '.\\csv_files'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Main execution
if __name__ == "__main__":
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver)
        save_df_to_csv(df, output_dir)
    finally:
        driver.quit()