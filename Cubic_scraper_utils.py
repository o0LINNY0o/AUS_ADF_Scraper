import os
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

def scrape_job_data(driver):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])

    url = 'https://cubic.wd1.myworkdayjobs.com/cubic_global_careers/jobs?Location_Country=d903bb3fedad45039383f6de334ad4db'
    driver.get(url)
    print(f"Scraping {url}")

    # Wait for the page to load and job results to appear
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-automation-id="jobResults"]')))
    
    # Add a small delay to ensure dynamic content loads
    time.sleep(1)

    current_page = 1

    while True:
        print(f"Scraping page {current_page}")
        
        # Wait for job listings to be visible
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-automation-id="jobResults"]')))
        
        soup = BeautifulSoup(driver.page_source, 'lxml')
        job_boxes = soup.select('li.css-1q2dra3')

        if not job_boxes:
            print("No job listings found on this page.")
            break

        for box in job_boxes:
            try:
                job_link = box.find('a', {'data-automation-id': 'jobTitle'})
                if not job_link:
                    continue
                    
                link_full = 'https://cubic.wd1.myworkdayjobs.com' + job_link.get('href')
                job_title = job_link.text.strip()

                location = 'N/A'
                location_element = box.select_one('[data-automation-id*="location"]')
                
                location = 'N/A'
                location_element = box.select_one('[data-automation-id="locations"] dd.css-129m7dg')
                if location_element:
                    location = location_element.text.strip()

                new_data = pd.DataFrame({
                    'Link': [link_full],
                    'Job Title': [job_title],
                    'Job Classification': ['N/A'],
                    'Location': [location],
                    'Company': ['Cubic']
                })

                df = pd.concat([df, new_data], ignore_index=True)
                print(f"Scraped job: {job_title} - {location}")

            except Exception as e:
                print(f"Error scraping job: {e}")

        # Check for the chevron-right icon
        next_chevron = soup.find('svg', {'class': 'wd-icon-chevron-right-small'})
        
        if not next_chevron:
            break
            
        # Find current page button
        current_page_button = soup.find('button', {'aria-current': 'page'})
        if current_page_button:
            try:
                page_num = int(current_page_button.text.strip())
                if page_num != current_page:
                    print(f"Page number mismatch. Expected {current_page}, found {page_num}")
                    break
            except ValueError:
                print("Could not parse page number")

        try:
            # Click the next page button using the chevron's parent element
            next_button = driver.find_element(By.CSS_SELECTOR, '.wd-icon-chevron-right-small')
            if next_button:
                # Click the parent button element
                parent_button = next_button.find_element(By.XPATH, './ancestor::button')
                parent_button.click()
                time.sleep(1)  # Wait for the next page to load
                current_page += 1
            else:
                print("Next button not found. Finishing scrape.")
                break

        except NoSuchElementException:
            print("Could not find next page button. Finishing scrape.")
            break
        except Exception as e:
            print(f"Error during pagination: {e}")
            break

    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'Cubic_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

# Create the .csv_files directory if it doesn't exist
output_dir = './csv_files'
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