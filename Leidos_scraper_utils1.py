import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
        raise

def click_show_more_for_location(driver, location_element):
    """Clicks 'Show more jobs' button for a specific location until no more jobs can be loaded."""
    max_attempts = 10
    attempts = 0
    
    while attempts < max_attempts:
        try:
            # Find the show more button for this location
            show_more = location_element.find_element(By.CSS_SELECTOR, "a.js-more")
            
            if not show_more.is_displayed():
                print(f"No more jobs to load for this location")
                return
            
            # Scroll to the button
            driver.execute_script("arguments[0].scrollIntoView(true);", show_more)
            time.sleep(1)
            
            # Click the button
            location_name = show_more.get_attribute('data-value')
            print(f"Clicking 'Show more jobs' for {location_name}")
            driver.execute_script("arguments[0].click();", show_more)
            
            # Wait for new content to load
            time.sleep(2)
            attempts += 1
            
        except StaleElementReferenceException:
            print("Element became stale, moving to next location")
            return
        except ElementClickInterceptedException:
            print("Click was intercepted, trying to scroll and click again")
            time.sleep(1)
            continue
        except Exception as e:
            print(f"Error clicking 'Show more jobs': {e}")
            return

def scrape_jobs_from_location_section(location_section):
    """Scrapes all job listings from a specific location section."""
    jobs_data = []
    
    try:
        # Find all job listings in this location section
        job_listings = location_section.find_elements(By.CSS_SELECTOR, 'li.opening-job')
        
        for job in job_listings:
            try:
                # Extract job details
                link = job.find_element(By.CSS_SELECTOR, 'a.link--block').get_attribute('href')
                job_title = job.find_element(By.CSS_SELECTOR, 'h4.details-title').text.strip()
                
                # Get location from the section header
                location = location_section.find_element(By.CSS_SELECTOR, 'h3.opening-title').text.strip()
                
                # Get job classification
                try:
                    job_classification = job.find_element(By.CSS_SELECTOR, 'span.margin--right--s').text.strip()
                except NoSuchElementException:
                    job_classification = 'Not specified'
                
                jobs_data.append({
                    'Link': link,
                    'Job Title': job_title,
                    'Job Classification': job_classification,
                    'Location': location,
                    'Company': 'Leidos'
                })
                
                print(f"Scraped: {job_title} - {location}")
                
            except Exception as e:
                print(f"Error scraping individual job: {e}")
                continue
                
    except Exception as e:
        print(f"Error scraping location section: {e}")
    
    return jobs_data

def scrape_job_data(driver):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])
    
    url = 'https://careers.smartrecruiters.com/Leidos1'
    driver.get(url)
    print(f"Scraping {url}")
    
    # Wait for the page to load initially
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'js-openings-load')))
    
    try:
        # Find all location sections
        while True:
            location_sections = driver.find_elements(By.CSS_SELECTOR, 'div.js-openings-load')
            
            if not location_sections:
                print("No location sections found")
                break
            
            for section in location_sections:
                try:
                    # Get location name
                    location_name = section.find_element(By.CSS_SELECTOR, 'h3.opening-title').text.strip()
                    print(f"\nProcessing location: {location_name}")
                    
                    # Click "Show more jobs" for this location until no more jobs
                    click_show_more_for_location(driver, section)
                    
                    # Scrape all jobs from this location
                    jobs_data = scrape_jobs_from_location_section(section)
                    
                    # Add to DataFrame
                    if jobs_data:
                        df = pd.concat([df, pd.DataFrame(jobs_data)], ignore_index=True)
                        print(f"Total jobs scraped so far: {len(df)}")
                    
                except StaleElementReferenceException:
                    print("Location section became stale, moving to next")
                    continue
                except Exception as e:
                    print(f"Error processing location section: {e}")
                    continue
            
            # Check if we need to load more locations
            try:
                load_more = driver.find_element(By.CSS_SELECTOR, 'a.js-more-locations')
                if load_more.is_displayed():
                    print("\nLoading more locations...")
                    driver.execute_script("arguments[0].click();", load_more)
                    time.sleep(2)
                else:
                    break
            except NoSuchElementException:
                print("\nNo more locations to load")
                break
            except Exception as e:
                print(f"Error loading more locations: {e}")
                break
                
    except Exception as e:
        print(f"Error during main scraping process: {e}")
    
    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'Leidos_job_data.csv')
    
    try:
        df.to_csv(file_path, index=False)
        print(f"\nData saved to {file_path}")
        print(f"Total jobs scraped: {len(df)}")
    except Exception as e:
        print(f"Error saving data to CSV: {e}")

# Create output directory
output_dir = '.\\csv_files'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Main execution
if __name__ == "__main__":
    driver = None
    try:
        driver = configure_webdriver()
        df = scrape_job_data(driver)
        save_df_to_csv(df, output_dir)
    except Exception as e:
        print(f"Error in main execution: {e}")
    finally:
        if driver:
            driver.quit()