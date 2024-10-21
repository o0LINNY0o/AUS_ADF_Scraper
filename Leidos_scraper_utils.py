import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import time

def configure_webdriver():
    try:
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
    except Exception as e:
        print(f"Error configuring webdriver: {e}")

def scrape_job_data(driver, Job_Classification, location):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])
   
    url = 'https://careers.smartrecruiters.com/Leidos1'
    driver.get(url)
    print(f"Scraping {url}")

    # Function to click "Show more jobs" links
    def click_show_more_jobs():
        try:
            show_more_links = driver.find_elements(By.CSS_SELECTOR, "a.js-more")
            if not show_more_links:
                return False
            
            for link in show_more_links:
                try:
                    if "Show more jobs" in link.text:
                        driver.execute_script("arguments[0].scrollIntoView(true);", link)
                        time.sleep(1)  # Short pause to allow page to settle after scrolling
                        driver.execute_script("arguments[0].click();", link)
                        print(f"Clicked 'Show more jobs' for {link.get_attribute('data-value')}")
                        WebDriverWait(driver, 10).until(EC.staleness_of(link))
                        return True  # Return True to continue the outer loop
                except StaleElementReferenceException:
                    print("Stale element reference encountered. Retrying...")
                    return True  # Continue the loop to find fresh elements
            
            # If we've gone through all links without clicking, return False
            return False
        except TimeoutException:
            print("Timeout while waiting for page to load.")
            return False
        except Exception as e:
            print(f"Error occurred while clicking 'Show more jobs': {e}")
            return False

    # Click all "Show more jobs" links
    while click_show_more_jobs():
        # Wait for the page to update
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'js-openings-load'))
        )
        time.sleep(2)  # Short pause to allow new content to load

    print("All 'Show more jobs' links have been clicked.")

    # Now scrape all visible job listings
    soup = BeautifulSoup(driver.page_source, 'lxml')
    job_listings = soup.find_all('li', class_='opening-job')
    
    for job in job_listings:
        try:
            link_element = job.find('a', class_='link--block')
            if not link_element:
                continue  # Skip if link element is not found
            link = 'https://careers.smartrecruiters.com' + link_element.get('href')
            print(f"Link: {link}")
            
            job_title_element = job.find('h4', class_='details-title job-title link--block-target')
            job_title = job_title_element.text.strip() if job_title_element else ''
            print(f"Job Title: {job_title}")
            
            company = 'Leidos'
            
            job_classification_element = job.find('span', class_='margin--right--s')
            Job_Classification = job_classification_element.text.strip() if job_classification_element else ''
            print(f"Job Classification: {Job_Classification}")
            
            location_element = job.find_previous('h3', class_='opening-title title display--inline-block text--default')
            location = location_element.text.strip() if location_element else ''
            print(f"Location: {location}")
            
            new_data = pd.DataFrame({
                'Link': [link], 
                'Job Title': [job_title], 
                'Job Classification': [Job_Classification],
                'Location': [location], 
                'Company': [company] })

            df = pd.concat([df, new_data], ignore_index=True)
            
        except Exception as e:
            print(f"Error scraping job: {e}")

    return df

output_dir = '.\\csv_files'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'Leidos_job_data.csv')

    try:
        df.to_csv(file_path, index=False)
        print(f"Data saved to {file_path}")
    except Exception as e:
        print(f"Error saving data to CSV: {e}")

if __name__ == "__main__":
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver, 'Engineering', 'Australia')
        save_df_to_csv(df, output_dir)
    except Exception as e:
        print(f"Error in main function: {e}")
    finally:
        driver.quit()
