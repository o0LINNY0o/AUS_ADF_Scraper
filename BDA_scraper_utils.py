import os
import pandas as pd
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

def configure_webdriver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument('--log-level=1')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Initialize the Chrome WebDriver
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
   
    url = 'https://jobs.boeing.com/category/boeing-defence-australia-jobs/185-18469/2681/1'
    driver.get(url)
    print(f"Scraping {url}")

    try:
        # Locate and click on the "Show All" link
        show_all_link = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//a[@class="pagination-show-all"]')))
        driver.execute_script("arguments[0].click();", show_all_link)
        
        # Wait for a fixed time (e.g., 5 seconds) to allow the page to load
        print("Clicked 'Show All' and waiting for page to load.")
        time.sleep(5)  # Adjust the sleep time as necessary

    except TimeoutException:
        print("Timeout waiting for 'Show All' link to be clickable")
        return df
    except NoSuchElementException:
        print("'Show All' link not found")
        return df
    except ElementClickInterceptedException:
        print("Unable to click 'Show All' link, it may be obscured")
        return df
    except Exception as e:
        print(f"Unexpected error when clicking 'Show All': {e}")
        return df

    soup = BeautifulSoup(driver.page_source, 'lxml')
    job_listings = soup.find_all('li', class_='no-security-clearance')
    
    if not job_listings:
        print("No job listings found.")
        return df

    for job in job_listings:
        try:
            link_element = job.find('a', class_='search-results__job-link')
            if not link_element:
                continue

            link = link_element.get('href')
            if not link:
                continue

            link_full = 'https://jobs.boeing.com' + link
                        
            job_title = job.find('span', class_='search-results__job-title').text.strip()
            
            company = 'BDA'
            
            location_element = job.find('span', class_='search-results__job-info location')
            location = location_element.text.strip() if location_element else ''
            print(f"Scraped job: {job_title} - {location}")

            new_data = pd.DataFrame({
                'Link': [link_full], 
                'Job Title': [job_title], 
                'Job Classification': [Job_Classification],
                'Location': [location], 
                'Company': [company]
            })

            df = pd.concat([df, new_data], ignore_index=True)
            
        except Exception as e:
            print(f"Error scraping job: {e}")

    return df

# Create the .csv_files directory if it doesn't exist
output_dir = './csv_files'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def save_df_to_csv(df, output_dir):
    # Ensure the directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Define the file path for the CSV
    file_path = os.path.join(output_dir, 'BDA_job_data.csv')

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