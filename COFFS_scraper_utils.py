import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
    """Scrape job listings from Coffs Harbour Recruitment Hub."""
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])

    url = 'https://coffsharbour.recruitmenthub.com.au/Positions-Vacant/'
    driver.get(url)
    print(f"Scraping {url}")

    # Wait for job listings to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'row.list'))
    )

    soup = BeautifulSoup(driver.page_source, 'lxml')
    job_listings = soup.find_all('div', class_='row list')

    if not job_listings:
        print("No job listings found.")
        return df

    for job in job_listings:
        try:
            # Find job link and title
            link_element = job.find('a', class_='title')
            if not link_element:
                continue

            # Full job link
            link_path = link_element.get('href')
            link_full = f'https://coffsharbour.recruitmenthub.com.au{link_path}'

            # Job title
            job_title = link_element.text.strip()

            # Location
            location_element = job.find('span', title=True)
            location = location_element.text.strip() if location_element else 'Not specified'

            # Create DataFrame row
            new_data = pd.DataFrame({
                'Link': [link_full],
                'Job Title': [job_title],
                'Job Classification': ['N/A'],
                'Location': [location],
                'Company': ['Coffs Harbour City Council']
            })

            df = pd.concat([df, new_data], ignore_index=True)
            print(f"Scraped job: {job_title} - {location}")

        except Exception as e:
            print(f"Error scraping individual job: {e}")

    return df

def save_df_to_csv(df, output_dir):
    """Save DataFrame to CSV file."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'Coffs_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

# Create output directory if it doesn't exist
output_dir = '.\\csv_files'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Main execution
if __name__ == "__main__":
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver)
        save_df_to_csv(df, output_dir)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()
