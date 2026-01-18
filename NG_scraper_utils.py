import os
import time
import pandas as pd
import json
import traceback
from seleniumbase import Driver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Global search URL to use as fallback
SEARCH_URL = 'https://jobs.northropgrumman.com/careers/search?query=%2A&location=australia&domain=ngc.com&sort_by=relevance'

def configure_driver():
    """Configure SeleniumBase driver with undetected mode."""
    driver = Driver(
        uc=True,
        headless=False,
        agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    return driver

def wait_for_page_load(driver, timeout=30):
    """Wait for the page to fully load."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.position-card[role='link']"))
        )
        print("Page loaded - position cards found")
        return True
    except TimeoutException:
        print("Timeout waiting for position cards")
        return False

def click_show_more_positions(driver, max_clicks=50):
    """Clicks 'Show More Positions' button until all jobs are loaded."""
    clicks = 0
    consecutive_failures = 0
    
    while clicks < max_clicks and consecutive_failures < 3:
        try:
            button = driver.find_element(By.CSS_SELECTOR, "button.show-more-positions")
            if button.is_displayed() and button.is_enabled():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", button)
                clicks += 1
                consecutive_failures = 0
                print(f"Clicked 'Show More Positions' ({clicks})")
                time.sleep(4)
            else:
                consecutive_failures += 1
                time.sleep(2)
        except NoSuchElementException:
            print("All jobs loaded (button gone)")
            break
        except Exception as e:
            consecutive_failures += 1
            if consecutive_failures >= 3: break
            time.sleep(2)
    return clicks

def extract_job_id_from_json(driver):
    """Extract job data from the JSON embedded in the page."""
    try:
        soup = BeautifulSoup(driver.page_source, 'lxml')
        script_tag = soup.find('code', {'id': 'smartApplyData'})
        
        if script_tag:
            json_text = script_tag.get_text(strip=True)
            data = json.loads(json_text)
            positions = data.get('positions', [])
            
            job_id_map = {}
            for pos in positions:
                title = pos.get('name', '')
                job_id = pos.get('id', '')
                location = pos.get('location', '').replace('Australia-', '')
                key = f"{title}|{location}"
                job_id_map[key] = {
                    'id': job_id,
                    'department': pos.get('department', 'N/A')
                }
            return job_id_map
    except Exception as e:
        print(f"Error extracting JSON: {e}")
    return {}

def extract_job_data_from_card(card, job_id_map):
    """Extract job information. Defaults Link to SEARCH_URL if ID not found."""
    try:
        # Initialize with SEARCH_URL as requested if specific link isn't found
        job_data = {
            'Link': SEARCH_URL, 
            'Job Title': 'N/A',
            'Job Classification': 'N/A',
            'Location': 'N/A',
            'Company': 'Northrop Grumman'
        }
        
        title_element = card.find('div', {'class': 'position-title'})
        if title_element:
            job_data['Job Title'] = title_element.get_text(strip=True)
        
        location_element = card.find('p', {'class': 'position-location'})
        if location_element:
            location = location_element.get_text(strip=True).replace('Australia-', '').strip()
            if ' and ' in location:
                location = location.split(' and ')[0].strip()
            job_data['Location'] = location
        
        classification_element = card.find('div', {'class': 'position-priority-container'})
        if classification_element:
            job_data['Job Classification'] = classification_element.get_text(strip=True)
        
        # Mapping logic
        key = f"{job_data['Job Title']}|{job_data['Location']}"
        job_id = None
        
        if key in job_id_map:
            job_id = job_id_map[key]['id']
        else:
            # Fallback: find by title only
            for map_key, map_value in job_id_map.items():
                if map_key.startswith(job_data['Job Title'] + "|"):
                    job_id = map_value['id']
                    break
        
        # If ID was found, construct the specific deep link
        if job_id:
            job_data['Link'] = f"https://jobs.northropgrumman.com/careers?location=australia&pid={job_id}&domain=ngc.com&sort_by=relevance"
        
        return job_data
    except Exception as e:
        print(f"Error extracting job card: {e}")
        return None

def scrape_job_cards_with_map(driver, job_id_map):
    jobs_data = []
    soup = BeautifulSoup(driver.page_source, 'lxml')
    job_cards = soup.find_all('div', {'class': 'position-card', 'role': 'link'})
    
    if not job_cards:
        job_cards = soup.find_all('div', {'data-test-id': lambda x: x and 'position-card-' in x})
    
    for idx, card in enumerate(job_cards):
        job_data = extract_job_data_from_card(card, job_id_map)
        if job_data:
            jobs_data.append(job_data)
    return jobs_data

def scrape_job_data(driver, job_classification_filter=None, location_filter=None):
    print(f"Navigating to {SEARCH_URL}")
    driver.get(SEARCH_URL)
    
    if not wait_for_page_load(driver):
        print("Initial load failed...")
    
    time.sleep(5)
    click_show_more_positions(driver)
    
    # Final page scroll to ensure all data is rendered
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)
    
    job_id_map = extract_job_id_from_json(driver)
    jobs_data = scrape_job_cards_with_map(driver, job_id_map)
    
    if job_classification_filter or location_filter:
        filtered_jobs = []
        for job in jobs_data:
            match_class = not job_classification_filter or job_classification_filter.lower() in job['Job Classification'].lower()
            match_loc = not location_filter or location_filter.lower() in job['Location'].lower()
            if match_class and match_loc:
                filtered_jobs.append(job)
        jobs_data = filtered_jobs
    
    return pd.DataFrame(jobs_data)

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    file_path = os.path.join(output_dir, f'NG_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

if __name__ == "__main__":
    output_dir = './csv_files'
    driver = None
    try:
        driver = configure_driver()
        df = scrape_job_data(driver)
        if not df.empty:
            save_df_to_csv(df, output_dir)
        else:
            print("No jobs found.")
    except Exception as e:
        print(f"Critical error: {e}")
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
