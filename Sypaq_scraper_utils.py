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

def wait_for_jobs_to_load(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "slide-up-item"))
        )
        time.sleep(1)  # Additional wait to ensure dynamic content loads
    except TimeoutException:
        print("Timeout waiting for jobs to load")

def scrape_job_data(driver):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])
   
    base_url = 'https://www.sypaq.com.au'
    job_url = base_url + '/careers-portal/#/jobs'
    driver.get(job_url)
    print(f"Scraping {job_url}")
    
    # Initial wait for page load
    wait_for_jobs_to_load(driver)

    processed_jobs = set()  # Keep track of processed jobs

    while True:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')
        job_cards = soup.find_all('a', class_='card slide-up-item')
        
        print(f"Found {len(job_cards)} job cards")
        
        if not job_cards:
            print("No jobs found. Stopping.")
            break
            
        # Process each job card
        for job_card in job_cards:
            try:
                # Extract job title
                title_elem = job_card.find('span', class_='card-title')
                job_title = title_elem.get_text(strip=True) if title_elem else "N/A"
                
                # Extract location
                location_elem = job_card.find('span', class_='card-location')
                location = location_elem.get_text(strip=True) if location_elem else "N/A"
                
                # Create job identifier
                job_identifier = f"{job_title}_{location}"
                
                # Skip if we've already processed this job
                if job_identifier in processed_jobs:
                    continue
                
                # Extract job link
                job_link = base_url + '/careers-portal/' + job_card['href'] if job_card.get('href') else "N/A"
                
                # Extract job classification
                classification_elem = job_card.find('span', class_='card-category')
                job_classification = classification_elem.get_text(strip=True) if classification_elem else "N/A"

                # Add company name
                company = "Sypaq"

                new_data = pd.DataFrame({
                    'Link': [job_link],
                    'Job Title': [job_title],
                    'Job Classification': [job_classification],
                    'Location': [location],
                    'Company': [company]
                })

                df = pd.concat([df, new_data], ignore_index=True)
                processed_jobs.add(job_identifier)
                print(f"Scraped job: {job_title} - {location}")
                
            except Exception as e:
                print(f"Error processing job card: {e}")
                continue
        
        try:
            # Check for "Load More" button
            load_more_button = driver.find_element(By.ID, 'load-more')
            
            # Check if button is disabled
            if 'disabled' in load_more_button.get_attribute('class'):
                print("Load More button is disabled. Stopping.")
                break
                
            # Scroll to the button and click it
            driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", load_more_button)
            print("Clicked 'Load More'")
            
            # Wait for new content
            time.sleep(1)
            wait_for_jobs_to_load(driver)
            
        except NoSuchElementException:
            print("No more jobs to load. Stopping.")
            break
        except Exception as e:
            print(f"Error clicking Load More button: {e}")
            break

    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'SYPAQ_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")
    print(f"Total jobs scraped: {len(df)}")

if __name__ == "__main__":
    output_dir = os.path.join(os.getcwd(), 'csv_files')
    
    driver = configure_webdriver()
    try:
        print("Starting job scraping...")
        df = scrape_job_data(driver)
        save_df_to_csv(df, output_dir)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()