import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

def configure_webdriver():
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

def scrape_job_data(driver, Job_Classification, location):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])
   
    url = 'https://www.kinexus.com.au/jobs'
    driver.get(url)
    print(f"Scraping {url}")

    last_page = False

    while True:
        soup = BeautifulSoup(driver.page_source, 'lxml')
        # Updated selector to find job listings
        job_listings = soup.find_all('li', {'class': 'job-result-item'})
        
        if not job_listings:
            print("No jobs found on current page")
            break
            
        for job in job_listings:
            try:
                # Find job link and title
                job_title_element = job.find('div', {'class': 'job-title'})
                if not job_title_element:
                    continue
                    
                link_element = job_title_element.find('a')
                if not link_element:
                    continue
                    
                link = link_element.get('href')
                if not link:
                    continue
                    
                link_full = 'https://www.kinexus.com.au' + link
                job_title = link_element.text.strip()
                
                # Find location
                location_element = job.find('li', {'class': 'results-job-location'})
                location = location_element.text.strip() if location_element else 'N/A'
                
                company = 'Kinexus'
                
                new_data = pd.DataFrame({
                    'Link': [link_full],
                    'Job Title': [job_title],
                    'Job Classification': [Job_Classification],
                    'Location': [location],
                    'Company': [company]
                })

                df = pd.concat([df, new_data], ignore_index=True)
                print(f"Scraped: {job_title} - {location}")
                
            except Exception as e:
                print(f"Error scraping job: {e}")

        if last_page:
            print("Finished scraping the last page. Stopping.")
            break

        # Find the next page link
        try:
            next_page_element = soup.find('a', {'rel': 'next'})
            if not next_page_element:
                print("No more pages to scrape. Stopping.")
                break
            
            next_page_url = 'https://www.kinexus.com.au' + next_page_element.get('href')
            
            if next_page_element.get('title') == 'Last Page':
                last_page = True
            
            driver.get(next_page_url)
            print(f"Moving to next page: {next_page_url}")
            
        except NoSuchElementException as e:
            print(f"No next page found: {e}")
            break

    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'Kinexus_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

# Main execution
if __name__ == "__main__":
    output_dir = '.\\csv_files'
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver, 'Engineering', 'Australia')
        save_df_to_csv(df, output_dir)
    finally:
        driver.quit()