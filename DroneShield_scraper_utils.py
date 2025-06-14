import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin
import time

def configure_webdriver():
    options = webdriver.ChromeOptions()
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

    url = 'https://ats.rippling.com/embed/droneshield/jobs?s=https%3A%2F%2Fwww.droneshield.com%2Fopen-positions&page=0&searchQuery=&workplaceType=&country=AU&state=&city='
    driver.get(url)
    print(f"Scraping {url}")

    current_page = 1

    while True:
        # Wait for the job boxes to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'css-aapqz6'))
        )

        soup = BeautifulSoup(driver.page_source, 'lxml')
        job_boxes = soup.find_all('div', class_='css-aapqz6')

        if not job_boxes:  # Check if no jobs are found on the current page
            print("No jobs found on this page. Stopping.")
            break

        print(f"Processing page {current_page}")
        
        for box in job_boxes:
            try:
                link_full = box.find('a', class_='css-1a75djn-Anchor e1tt4etm0')['href']
                job_title = box.find('a', class_='css-1a75djn-Anchor e1tt4etm0').text.strip()
                company = 'DroneShield'

                job_classification = box.find('span', {'data-icon': 'DEPARTMENTS_OUTLINE'}).find_next('p', class_='css-htb71u-Body1Element').text.strip()
                location = box.find('span', {'data-icon': 'LOCATION_OUTLINE'}).find_next('p', class_='css-htb71u-Body1Element').text.strip()

                new_data = pd.DataFrame({
                    'Link': [link_full],
                    'Job Title': [job_title],
                    'Job Classification': [job_classification],
                    'Location': [location],
                    'Company': [company] })

                df = pd.concat([df, new_data], ignore_index=True)
                print(f"Scraped job: {job_title} - {location}")
            except Exception as e:
                print(f"Error scraping job: {e}")

        # Check if we're on the last page by examining the next page button
        try:
            # Look for the next page button with tabindex="-1" which indicates it's disabled (last page)
            next_page_buttons = driver.find_elements(By.CSS_SELECTOR, 'a[aria-label="Next page"]')
            
            if not next_page_buttons:
                print("No next page button found. Stopping.")
                break
                
            next_page_button = next_page_buttons[0]
            tabindex = next_page_button.get_attribute('tabindex')
            
            if tabindex == "-1":
                print("Reached the last page (next button disabled). Stopping.")
                break
                
            # Use JavaScript to click the next page button
            driver.execute_script("arguments[0].click();", next_page_button)
            
            # Increment page counter
            current_page += 1
            
            # Wait for the next page to load
            time.sleep(2)

        except NoSuchElementException as e:
            print(f"No next page found: {e}")
            break
        except ElementClickInterceptedException as e:
            print(f"Element click intercepted: {e}")
            break
        except Exception as e:
            print(f"Error navigating to next page: {e}")
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
    file_path = os.path.join(output_dir, 'Droneshield_job_data.csv')

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