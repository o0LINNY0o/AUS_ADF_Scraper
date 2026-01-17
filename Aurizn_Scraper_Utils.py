import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium_stealth import stealth
import time
import re

def configure_webdriver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument('--log-level=3')
    options.add_argument('--disable-background-networking') 
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Standard Chrome Driver setup
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
    # Initialize list for dictionary storage (more efficient than repeated concat)
    jobs_data = []
    
    url = 'https://aurizn.co/careers/jobs/'
    print(f"Scraping {url}")

    driver.get(url)
    
    # Allow time for the Brizy builder elements to render
    time.sleep(3) 
    
    try:
        print("Processing page...")
        soup = BeautifulSoup(driver.page_source, 'lxml')
        
        # 1. Extract the generic "Apply" link (SEEK) to use as the job link
        # Since the list items are just text, we direct users to the main Seek portal
        base_link = url # Default to current page
        seek_btn = soup.select_one('a[href*="seek.com.au"]')
        if seek_btn:
            base_link = seek_btn.get('href')
        
        # 2. Find the list items containing job descriptions
        # We look for the rich text div, then the UL, then LI items
        # Based on your HTML: <li class="brz-tp-lg-paragraph ...">
        job_items = soup.select('.brz-rich-text ul li')
        
        if not job_items:
            print("No job list found. Checking alternative selectors...")
            # Fallback in case class names change slightly
            job_items = soup.select('ul li')

        print(f"Found {len(job_items)} list items. Parsing...")

        for index, item in enumerate(job_items, 1):
            try:
                full_text = item.text.strip()
                
                # Skip empty lines
                if not full_text:
                    continue

                # Logic to split "Job Title – Location"
                # We use regex to handle both En-dash (–) and Hyphen (-) and surrounding spaces
                split_data = re.split(r'\s+[–-]\s+', full_text, maxsplit=1)
                
                job_title = split_data[0].strip()
                
                if len(split_data) > 1:
                    location = split_data[1].strip()
                else:
                    location = "Australia (Unspecified)" # Fallback if no dash found

                # Job Classification is not present in the text list, leaving empty or generic
                Job_Classification = "N/A" 

                print(f"Scraped: {job_title} - {location}")

                jobs_data.append({
                    'Link': base_link,
                    'Job Title': job_title,
                    'Job Classification': Job_Classification,
                    'Location': location,
                    'Company': 'Aurizn'
                })
                
            except Exception as e:
                print(f"Error processing item {index}: {e}")

    except Exception as e:
        print(f"Error processing jobs: {e}")

    # Convert list of dicts to DataFrame
    df = pd.DataFrame(jobs_data, columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])
    print(f"Total jobs scraped: {len(df)}")
    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'AURIZN_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

if __name__ == "__main__":
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver)
        if not df.empty:
            save_df_to_csv(df, '.\\csv_files')
        else:
            print("No data extracted.")
    finally:
        driver.quit()