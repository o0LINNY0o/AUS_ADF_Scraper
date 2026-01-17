import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
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
    jobs_data = []
    
    url = 'https://aurizn.co/careers/jobs/'
    print(f"Scraping {url}")

    driver.get(url)
    time.sleep(3) # Wait for Brizy builder to render
    
    try:
        print("Processing page...")
        soup = BeautifulSoup(driver.page_source, 'lxml')
        
        # 1. Get the Generic Apply Link (SEEK)
        # We need this because the text items don't have individual links
        base_link = url 
        seek_btn = soup.select_one('a[href*="seek.com.au"]')
        if seek_btn:
            base_link = seek_btn.get('href')

        # 2. LOCATE THE SPECIFIC JOB LIST
        # Strategy: Find the text "We are currently recruiting for:" and get the next <ul>
        job_items = []
        
        # Find the header paragraph
        header_p = soup.find(lambda tag: tag.name == "p" and "recruiting for" in tag.text)
        
        if header_p:
            print("Found 'Recruiting for' header. Extracting list...")
            target_ul = header_p.find_next_sibling('ul')
            if target_ul:
                job_items = target_ul.find_all('li')
        
        # Fallback: If header text changed, try the specific container ID from your HTML
        if not job_items:
            print("Header not found, trying container ID...")
            container = soup.find('div', {'data-brz-custom-id': 'swkxqxpemvkfehwfzxofkztzbyrljeflluth'})
            if container:
                job_items = container.select('ul li')

        # Fallback 2: Try the specific class on the LI elements
        if not job_items:
            print("Container not found, trying specific classes...")
            job_items = soup.select('li.brz-tp-lg-paragraph')

        print(f"Found {len(job_items)} valid job items.")

        for index, item in enumerate(job_items, 1):
            try:
                full_text = item.text.strip()
                
                if not full_text:
                    continue

                # Clean up invisible characters if present
                full_text = full_text.replace('\u200b', '').replace('\xa0', ' ')

                # Split Title and Location based on Dash or En-dash
                # Regex handles: "Title - Location" or "Title – Location" with spaces around
                split_data = re.split(r'\s+[–-]\s+', full_text, maxsplit=1)
                
                job_title = split_data[0].strip()
                
                if len(split_data) > 1:
                    location = split_data[1].strip()
                else:
                    # If no dash is found, assume the whole text is the title or check for common cities
                    location = "Australia" 
                    # specific check for Adelaide/Canberra if dash is missing
                    if "Adelaide" in job_title: location = "Adelaide"
                    elif "Canberra" in job_title: location = "Canberra"

                print(f"Scraped: {job_title} - {location}")

                jobs_data.append({
                    'Link': base_link,
                    'Job Title': job_title,
                    'Job Classification': 'Unspecified',
                    'Location': location,
                    'Company': 'Aurizn'
                })
                
            except Exception as e:
                print(f"Error processing item {index}: {e}")

    except Exception as e:
        print(f"Error processing jobs: {e}")

    df = pd.DataFrame(jobs_data, columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])
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
            print("No jobs found.")
    finally:
        driver.quit()