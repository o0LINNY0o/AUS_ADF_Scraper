# milskil_scraper_selenium_final.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import traceback

# --- Configuration ---
base_url = "https://milskil.com"
careers_url = f"{base_url}/careers/"

chrome_options = Options()
chrome_options.add_argument("--headless")  # Uncomment to run in background
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# chromedriver_path = '/path/to/chromedriver' # Set if chromedriver is not in PATH

# --- End Configuration ---


# --- Setup WebDriver ---
try:
    # service = Service(executable_path=chromedriver_path) # Use if path is set
    # driver = webdriver.Chrome(service=service, options=chrome_options)
    driver = webdriver.Chrome(options=chrome_options) # Assumes chromedriver is in PATH
    print("Chrome WebDriver initialized.")
except Exception as e:
    print(f"Error initializing Chrome WebDriver: {e}")
    traceback.print_exc()
    print("Please ensure ChromeDriver is installed and in your PATH.")
    exit(1)

wait = WebDriverWait(driver, 15) # Wait up to 15 seconds

# --- Navigate, Handle Iframe, and Retrieve HTML ---
try:
    print(f"Navigating to {careers_url}...")
    driver.get(careers_url)

    # 1. Wait for the iframe element to be present on the main page
    iframe_selector = "iframe#elmo-recruitment-embed"
    print(f"Waiting for iframe '{iframe_selector}' to be present...")
    iframe_element = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, iframe_selector))
    )
    print(f"Iframe '{iframe_selector}' is present.")

    # 2. Switch the WebDriver's context to the iframe
    print(f"Switching to iframe '{iframe_selector}'...")
    driver.switch_to.frame(iframe_element)
    print("Successfully switched to iframe context.")

    # 3. Wait for the job listings container (#section-list) to load inside the iframe
    section_list_id = "section-list"
    print(f"Waiting for '#{section_list_id}' inside the iframe...")
    section_list_element = wait.until(
        EC.presence_of_element_located((By.ID, section_list_id))
    )
    print(f"'#{section_list_id}' found inside the iframe.")

    # 4. Get the HTML source *from within the iframe*
    iframe_html_content = driver.page_source
    print("HTML content retrieved from within the iframe.")

except Exception as e:
    print(f"An error occurred during navigation or waiting: {e}")
    traceback.print_exc()
    driver.quit()
    exit(1)

# --- Scrape Data from Iframe HTML ---
try:
    # Parse the HTML content retrieved from the iframe
    soup = BeautifulSoup(iframe_html_content, 'html.parser')

    # Find the section-list div
    section_list = soup.find('div', {'id': section_list_id})
    if not section_list:
        raise Exception(f"Could not find #{section_list_id} div in parsed iframe HTML.")

    # Find the list-group ul containing job items
    job_list = section_list.find('ul', {'class': 'list-group'})
    if not job_list:
        raise Exception("Could not find ul.list-group within #section-list.")

    # List to store job data
    jobs_data = []
    iframe_base_url = "https://milskil.elmotalent.com.au" # Base URL for links inside iframe

    # Loop through each job item (li.list-group-item)
    job_items = job_list.find_all('li', class_='list-group-item')
    print(f"Found {len(job_items)} job items in the list.")
    for job_item in job_items:
        try:
            # --- Extract Job Title and Link ---
            title_tag = job_item.find('a', class_='redirect_elmo_link')
            if not title_tag:
                print("Warning: Found a list-group-item without a redirect_elmo_link")
                continue

            job_title = title_tag.get_text(strip=True)
            relative_link = title_tag.get('href')
            if not relative_link:
                print(f"Warning: Found a link tag without href for job '{job_title}'")
                continue

            # Construct full link based on iframe's base URL
            if relative_link.startswith('/'):
                link_full = iframe_base_url + relative_link
            else:
                link_full = iframe_base_url + '/' + relative_link

            # --- Extract Location ---
            location = 'N/A' # Default value
            # Find the div containing location info based on the new structure
            # Looking for the div with class 'col-md-4 col-sm-4 col-xs-12'
            location_container_div = job_item.find('div', class_='col-md-4 col-sm-4 col-xs-12')
            if location_container_div:
                # The text is directly inside the nested div
                # Example: <div class="col-md-10 col-sm-10 col-xs-10">RAAF Base Williamtown, NSW</div>
                location_text_div = location_container_div.find('div', class_='col-md-10')
                if location_text_div:
                    # Assign the entire raw text as the location
                    location = location_text_div.get_text(strip=True)

            # --- Append Data ---
            jobs_data.append({
                'Link': link_full,
                'Job Title': job_title,
                'Job Classification': 'N/A',
                'Location': location,
                'Company': 'MILSKIL'
            })
            print(f"Found job: {job_title} - {location} - {link_full}")

        except Exception as e:
            print(f"Error parsing job item: {e}")
            continue # Continue with the next item

    # --- Save Data to CSV ---
    # Corrected the typo here: 'jobs_' -> 'jobs_data'
    if jobs_data:
        df = pd.DataFrame(jobs_data)
        output_filename = 'milskil_jobs.csv'
        df.to_csv(output_filename, index=False)
        print(f"\nScraped {len(df)} jobs. Saved to '{output_filename}'")
    else:
        print("\nNo jobs were scraped.")

except Exception as e:
    print(f"An error occurred during scraping or saving: {e}")
    traceback.print_exc()

finally:
    # --- Cleanup ---
    # Switch back to the main content (good practice)
    print("Switching driver context back to the main page...")
    driver.switch_to.default_content()
    print("Switched back to main page context.")
    # Quit the driver
    print("Closing the browser...")
    driver.quit()
    print("Browser closed.")
