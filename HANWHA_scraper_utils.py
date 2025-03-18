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
    """Configures the Selenium WebDriver."""
    options = webdriver.ChromeOptions()
    options.add_argument('--log-level=1')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # options.add_argument('--headless')  # Optional: Run headless
    options.add_argument('--disable-gpu')

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

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
    """Scrapes job data from within the iframe."""
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])

    url = 'https://www.hanwha-defence.com.au/careers'
    driver.get(url)
    print(f"Scraping {url}")

    # --- Crucial: Switch to the iframe ---
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "iframe_listing"))
        )
        iframe = driver.find_element(By.ID, "iframe_listing")
        driver.switch_to.frame(iframe)
        print("Switched to iframe")
    except TimeoutException:
        print("Error: Timeout waiting for the iframe to load.")
        return df
    # --- Inside the iframe ---
    try:
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.row.default"))
        )
        print("Found at least one 'row default' element within the iframe")
    except TimeoutException:
        print("Error: Timeout waiting for job rows inside the iframe.")
        driver.switch_to.default_content() # Switch back before returning
        return df

    while True:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')

        job_rows = soup.find_all('div', class_='row default')
        print(f"Found {len(job_rows)} job rows")

        if not job_rows:
            print("No job rows found on this page.")
            break
        
        for row in job_rows:
            try:
                job_title_elem = row.find('h2', class_='jobName_h2')
                job_title = job_title_elem.text.strip() if job_title_elem else "N/A"

                job_category_elem = row.find('h6', class_='jobCategory')
                job_classification = job_category_elem.text.strip() if job_category_elem else "N/A" #Renamed to job_classification

                # Construct the link using Job ID (more reliable than apply ID)
                details_button = row.find('a', class_='btnJobDetails')
                job_id = "N/A"
                if details_button and 'onclick' in details_button.attrs:
                    onclick_str = details_button['onclick']
                    start = onclick_str.find("('") + 2
                    end = onclick_str.find("')")
                    if start > 1 and end > start:
                        job_id = onclick_str[start:end]

                #link = f"https://www.hanwha-defence.com.au/job-details/{job_id}" if job_id != "N/A" else "N/A" # Corrected link construction
                link = f"https://hanwha-defense.sentrient.online/RecruitmentJob/Careers#{job_id}" if job_id != "N/A" else "N/A" # Corrected link construction


                print(f"Scraped job: {job_title}")
                new_data = pd.DataFrame({
                    'Link': [link],
                    'Job Title': [job_title],
                    'Job Classification': [job_classification],
                    'Location': ['N/A'],  # Hardcoded as per requirement
                    'Company': ['HANWHA'] # Hardcoded as per requirement
                })
                df = pd.concat([df, new_data], ignore_index=True)

            except Exception as e:
                print(f"Error scraping job details: {e}")

        # --- Load More (inside iframe) ---
        try:
            load_more_button = driver.find_element(By.ID, 'load-more')
            if "disabled" not in load_more_button.get_attribute("class"):
                driver.execute_script("arguments[0].click();", load_more_button)
                print("Clicked 'Load More'")
                # Wait for *new* content to load *inside* the iframe
                WebDriverWait(driver, 10).until(
                    lambda driver: len(driver.find_elements(By.CSS_SELECTOR, "div.row.default")) > len(job_rows)
                )

            else:
                print("Load More button is disabled.  No more jobs.")
                break

        except NoSuchElementException:
            print("No 'Load More' button found. Finished scraping.")
            break
        except TimeoutException:
            print("Timeout waiting for new jobs to load after clicking 'Load More'.")
            break
        except Exception as e:
            print(f"Error clicking 'Load More': {e}")
            break

    driver.switch_to.default_content()  # Switch back to the main page
    return df

def save_df_to_csv(df, output_dir='./csv_files'):
    """Saves the DataFrame."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(output_dir, f'hanwha_jobs_{timestamp}.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

if __name__ == "__main__":
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver)
        if not df.empty:
            save_df_to_csv(df)
            print(f"Successfully scraped {len(df)} jobs")
        else:
            print("No jobs were scraped.")
    finally:
        driver.quit()