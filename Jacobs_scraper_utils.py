import os
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

def configure_webdriver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument('--log-level=1')
    options.add_argument("--window-size=1920,1080")
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
   
    url = 'https://careers.jacobs.com/en_US/careers/SearchJobs/?4182=%5B76334%5D&4182_format=4422&listFilterMode=1&jobRecordsPerPage=10&'
    driver.get(url)
    print(f"Scraping {url}")
    
    # Wait for page to load
    time.sleep(5)

    while True:
        soup = BeautifulSoup(driver.page_source, 'lxml')
        # Find all job articles
        job_listings = soup.find_all('article', {'class': 'article--result'})
        
        if not job_listings:
            print("No jobs found on current page")
            break
            
        print(f"Found {len(job_listings)} jobs on current page")
        
        for job in job_listings:
            try:
                # Find job link and title
                link_element = job.find('a', {'class': 'link'})
                if not link_element:
                    continue
                    
                link = link_element.get('href')
                if not link:
                    continue
                    
                job_title = link_element.text.strip()
                
                # Find location
                location_element = job.find('span', {'class': 'list-item-location'})
                location = location_element.text.strip() if location_element else 'N/A'
                
                # Find job classification
                classification_element = job.find('span', {'class': 'list-item-capabilities'})
                job_classification = classification_element.text.strip() if classification_element else 'N/A'

                company = 'Jacobs'
                
                # Apply filters if specified
                if Job_Classification and Job_Classification.lower() not in job_classification.lower():
                    continue
                    
                if location and location.lower() not in location.lower():
                    continue
                print(f"Scraped job: {job_title} - {location}")

                new_data = pd.DataFrame({
                    'Link': [link],
                    'Job Title': [job_title],
                    'Job Classification': [job_classification],
                    'Location': [location],
                    'Company': [company]
                })

                df = pd.concat([df, new_data], ignore_index=True)
                print(f"Scraped: {job_title} - {location}")
                
            except Exception as e:
                print(f"Error scraping job: {e}")

        # Find the next page button
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, 'a[aria-label*="Next"]')
            if not next_button.is_enabled():
                print("Reached last page")
                break
                
            next_button.click()
            print("Moving to next page")
            time.sleep(3)  # Wait for new page to load
            
        except NoSuchElementException:
            print("No more pages available")
            break
        except Exception as e:
            print(f"Error navigating to next page: {e}")
            break

    print(f"Total jobs scraped: {len(df)}")
    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'Jacobs_job_data.csv')  # Changed filename to Jacobs
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

# Main execution
if __name__ == "__main__":
    output_dir = '.\\csv_files'
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver, None, None)  # Remove filters for testing
        if not df.empty:
            save_df_to_csv(df, output_dir)
        else:
            print("No jobs were found matching the criteria")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()