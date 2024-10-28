import os
import time
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

def configure_webdriver():
    options = webdriver.ChromeOptions()
    #options.add_argument("--headless")
    options.add_argument('--log-level=1')
    options.add_argument("--window-size=1920,1080")
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

def expand_all_show_more(driver):
    """Expands all 'show more' buttons on the current page."""
    try:
        # Find all show more buttons
        show_more_buttons = driver.find_elements(By.CLASS_NAME, "show-more-link")
        if show_more_buttons:
            print(f"Found {len(show_more_buttons)} 'show more' buttons to expand")
            # Click all buttons using JavaScript
            for button in show_more_buttons:
                driver.execute_script("arguments[0].click();", button)
            time.sleep(1)  # Brief wait for expansion
            return True
    except Exception as e:
        print(f"Error expanding 'show more' buttons: {e}")
    return False

def scrape_current_page(soup):
    """Scrapes job data from the current page's soup."""
    jobs_data = []
    job_listings = soup.find_all('div', {'class': 'JobListingCard__Container-sc-dablja-0'})

    if not job_listings:
        print("No jobs found on current page")
        return jobs_data

    print(f"Found {len(job_listings)} jobs on current page")

    for job in job_listings:
        try:
            # Find job link and title
            link_element = job.find('a')
            if not link_element:
                continue

            link = link_element.get('href')
            if not link:
                continue

            # Make the link absolute
            if link.startswith('/'):
                link = 'https://www.northropgrumman.com' + link

            job_title = link_element.find('h2').text.strip() if link_element.find('h2') else ''

            # Find locations
            location_elements = job.find_all('span', {'class': 'location'})
            locations = ', '.join([loc.text.strip().replace('|', '') for loc in location_elements])

            # Extract job classification from URL
            job_classification = link.split('/')[2] if len(link.split('/')) > 2 else 'N/A'

            jobs_data.append({
                'Link': link,
                'Job Title': job_title,
                'Job Classification': job_classification,
                'Locations': locations,
                'Company': 'Northrop Grumman'
            })

            print(f"Scraped: {job_title} - {locations}")

        except Exception as e:
            print(f"Error scraping job: {e}")

    return jobs_data

def scrape_job_data(driver, Job_Classification, location):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Locations', 'Company'])

    url = 'https://www.northropgrumman.com/jobs?country=australia'
    driver.get(url)
    print(f"Scraping {url}")

    # Wait for initial page load
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "JobListingCard__Container-sc-dablja-0")))
    time.sleep(3)

    page_number = 1
    all_jobs_data = []

    while True:
        print(f"\nProcessing page {page_number}")

        # Expand all "show more" buttons on current page
        expand_all_show_more(driver)

        # Scrape the current page
        soup = BeautifulSoup(driver.page_source, 'lxml')
        jobs_data = scrape_current_page(soup)

        # Apply filters if specified
        if Job_Classification or location:
            filtered_jobs = []
            for job in jobs_data:
                if Job_Classification and Job_Classification.lower() not in job['Job Classification'].lower():
                    continue
                if location and location.lower() not in ','.join(job['Locations']).lower():
                    continue
                filtered_jobs.append(job)
            jobs_data = filtered_jobs

        all_jobs_data.extend(jobs_data)

        # Check for next page
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, 'a.filter-search-page.next[rel="next"]')
            if next_button.get_attribute('aria-disabled') == 'true':
                print("Reached last page")
                break

            driver.execute_script("arguments[0].click();", next_button)
            print("Moving to next page")
            page_number += 1
            time.sleep(3)  # Wait for new page to load

        except NoSuchElementException:
            print("No more pages available")
            break
        except Exception as e:
            print(f"Error navigating to next page: {e}")
            break

    # Convert all jobs data to DataFrame
    df = pd.DataFrame(all_jobs_data)
    print(f"\nTotal jobs scraped: {len(df)}")
    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    file_path = os.path.join(output_dir, f'NG_job_data_{timestamp}.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

# Main execution
if __name__ == "__main__":
    output_dir = '.\\csv_files'
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver, None, None)  # Remove filters for testing
        if not df.empty:
            save_df_to_csv(df, output_dir)
        else:
            print("No jobs were found matching the criteria")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()
