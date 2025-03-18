import os
import pandas as pd
import time
from selenium import webdriver
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def configure_webdriver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode
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

def scrape_job_data(driver):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])
    url = 'https://www.midcoast.nsw.gov.au/Your-Council/Working-with-us/Current-vacancies'
    driver.get(url)
    print(f"Scraping {url}")

    # Wait for the iframe to be present and switch to it
    try:
        WebDriverWait(driver, 30).until(
            EC.frame_to_be_available_and_switch_to_it((By.NAME, "scout_iframe"))
        )
    except TimeoutException:
        print("Timed out waiting for the iframe to load.")
        return df

    # Wait for job listings to load *inside* the iframe
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-list tbody tr"))
        )
    except TimeoutException:
        print("Timed out waiting for job listings inside the iframe to load.")
        driver.switch_to.default_content()  # Switch back to the main content
        return df

    # Find job listings *inside* the iframe using Selenium
    job_listings = driver.find_elements(By.CSS_SELECTOR, "table.table-list tbody tr")

    if not job_listings:
        print("No job listings found inside the iframe.")
        driver.switch_to.default_content()
        return df

    for job in job_listings:
        try:
            # Job Title and Link (inside the iframe)
            link_element = job.find_element(By.CSS_SELECTOR, "td.align-middle a.job_title")
            job_title = link_element.text.strip()
            link_full = link_element.get_attribute('href')

            # Create DataFrame row
            new_data = pd.DataFrame({
                'Link': [link_full],
                'Job Title': [job_title],
                'Job Classification': ['N/A'],
                'Location': ['N/A'],
                'Company': ['Mid Coast City Council']
            })

            df = pd.concat([df, new_data], ignore_index=True)
            print(f"Scraped job: {job_title}")

        except Exception as e:
            print(f"Error scraping individual job inside iframe: {e}")
            continue  # Move to the next job if there's an error

    driver.switch_to.default_content()  # Switch back to the main content after scraping
    return df

def save_df_to_csv(df, output_dir):
    """Save DataFrame to CSV file."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'MIDC_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

# Create output directory
output_dir = '.\\csv_files'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Main execution
if __name__ == "__main__":
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver)
        if not df.empty:
            save_df_to_csv(df, output_dir)
        else:
            print("No data to save.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()
