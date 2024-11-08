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
   
    url = 'https://www.careers-page.com/c4isolutions#openings'
    driver.get(url)
    print(f"Scraping {url}")

    while True:
        soup = BeautifulSoup(driver.page_source, 'lxml')
        job_listings = soup.find_all('li', class_='media')
        
        if not job_listings:
            print("No job listings found on this page.")
            break

        for job in job_listings:
            try:
                link_element = job.find('a', class_='text-secondary')
                if not link_element: continue
                link = link_element.get('href')
                link_full = 'https://www.careers-page.com' + link
                
                job_title = link_element.find('h5', class_='mt-0 mb-1 primary-color').text.strip()
                
                company = 'C4iSolutions'
                
                Job_Classification = 'N/A'
                
                location_element = job.find('span', class_='text-secondary')
                if location_element:
                    location_icon = location_element.find('i', class_='fas fa-map-marker-alt')
                    if location_icon:
                        location = location_icon.next_sibling.strip()
                    else:
                        location = location_element.text.strip()
                else:
                    location = ''
                print(f"Scraped job: {job_title} - {location}")
                
                new_data = pd.DataFrame({
                    'Link': [link_full], 
                    'Job Title': [job_title], 
                    'Job Classification': [Job_Classification],
                    'Location': [location], 
                    'Company': [company] })

                df = pd.concat([df, new_data], ignore_index=True)
                
            except Exception as e:
                print(f"Error scraping job: {e}")

        # Check if there's a "Load More" button
        try:
            load_more_button = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CLASS_NAME, 'btn-')))
            driver.execute_script("arguments[0].click();", load_more_button)
            print("Clicked 'Load More' button. Loading more jobs...")
            # Wait for new content to load
            WebDriverWait(driver, 1).until(EC.staleness_of(job_listings[-1]))
        except:
            print("No more jobs to load or couldn't find 'Load More' button.")
            break

    return df

# Create the .csv_files directory if it doesn't exist
output_dir = '.\\csv_files'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'C4i_job_data.csv')

    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")


# Main execution
if __name__ == "__main__":
    driver = configure_webdriver()
    try:
        df = scrape_job_data(driver, 'Engineering', 'Australia')
        save_df_to_csv(df, output_dir)
    finally:
        driver.quit()
