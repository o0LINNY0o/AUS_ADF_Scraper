import os
import time
import pandas as pd
from bs4 import BeautifulSoup
from seleniumbase import Driver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
import traceback

def configure_webdriver():
    driver = Driver(uc=True, headless=True)
    return driver

def wait_for_jobs(driver, timeout=30):
    wait = WebDriverWait(driver, timeout)
    try:
        selectors = [
            (By.CSS_SELECTOR, "[data-ph-at-id='jobs-list']"),
            (By.CSS_SELECTOR, ".jobs-list-item"),
            (By.CSS_SELECTOR, "[data-ph-at-id='job-link']"),
            (By.CSS_SELECTOR, ".content-block"),
            (By.CSS_SELECTOR, "[ph-tevent='job_click']")
        ]

        for selector in selectors:
            try:
                wait.until(EC.presence_of_element_located(selector))
                return True
            except TimeoutException:
                continue

        return False
    except Exception as e:
        print(f"Error waiting for jobs: {e}")
        return False

def scrape_current_page(driver):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])

    soup = BeautifulSoup(driver.page_source, 'lxml')

    jobs = (soup.find_all('a', {'data-ph-at-id': 'job-link'}) or
           soup.find_all('a', {'ph-tevent': 'job_click'}) or
           soup.select('.jobs-list-item a'))

    for job in jobs:
        try:
            link = job.get('href', '')
            if not link.startswith('http'):
                link = 'https://careers.rtx.com' + link

            job_title = (job.get('data-ph-at-job-title-text', '') or
                       job.select_one('.job-title span')
                       ).strip()

            location = (job.get('data-ph-at-job-location-text', '') or
                      job.select_one('.job-location')
                      ).strip()

            job_classification = (job.get('data-ph-at-job-category-text', '') or
                                job.select_one('.job-category')
                                ).strip()

            print(f"Scraped: {job_title} - {location}")

            new_data = pd.DataFrame({
                'Link': [link],
                'Job Title': [job_title],
                'Job Classification': [job_classification],
                'Location': [location],
                'Company': ['Collins Aero']
            })

            df = pd.concat([df, new_data], ignore_index=True)

        except Exception as e:
            print(f"Error scraping individual job: {e}")
            continue

    return df

def check_next_button_exists(driver):
    try:
        next_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//ppc-content[text()="Next"]'))
        )
        return True
    except TimeoutException:
        return False

def scrape_job_data(driver):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])
    url = 'https://careers.rtx.com/global/en/collins-aerospace-search-results-general'

    try:
        driver.get(url)

        # Select Australia by text
        australia_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//span[text()="Australia"]'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", australia_button)
        driver.execute_script("arguments[0].click();", australia_button)
        time.sleep(1)

        if not wait_for_jobs(driver):
            print("Failed to load jobs page")
            return df

        page_num = 1
        while True:
            print(f"Scraping page {page_num}")

            current_page_jobs = scrape_current_page(driver)
            if not current_page_jobs.empty:
                df = pd.concat([df, current_page_jobs], ignore_index=True)
            else:
                print(f"No jobs found on page {page_num}")

            if not check_next_button_exists(driver):
                print("Next button not found - reached last page")
                break

            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//ppc-content[text()="Next"]'))
                )
                next_button.click()
            except TimeoutException:
                print("Next button not found or clickable - reached last page")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                break

    except Exception as e:
        print(f"Error during scraping: {e}")
        traceback.print_exc()  # Print the full traceback

    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    file_path = os.path.join(output_dir, f'Collins_job_data_{timestamp}.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

def main():
    output_dir = '.\\csv_files'
    driver = configure_webdriver()
    df = scrape_job_data(driver)

    if not df.empty:
        save_df_to_csv(df, output_dir)
        print(f"Successfully scraped {len(df)} jobs")

    driver.quit()

if __name__ == "__main__":
    main()
