import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

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


def scrape_job_data(driver, job_classification="N/A", location="N/A"):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])
   
    url = 'https://www.careers-page.com/c4isolutions#openings'
    driver.get(url)
    print(f"Scraping {url}")
    
    # Wait for the page to load properly
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'media'))
    )
    
    # Initial page load
    time.sleep(1)  # Give a moment for JS to render content

    while True:
        soup = BeautifulSoup(driver.page_source, 'lxml')
        job_listings = soup.find_all('li', class_='media')
        
        if not job_listings:
            print("No job listings found on this page.")
            break

        for job in job_listings:
            try:
                link_element = job.find('a', class_='text-secondary')
                if not link_element: 
                    continue
                    
                link = link_element.get('href')
                link_full = 'https://www.careers-page.com' + link
                
                job_title_element = link_element.select_one('h5.job-position-break')
                if job_title_element:
                    # Clean up the job title by removing any bookmark icons
                    for icon in job_title_element.find_all('i'):
                        icon.decompose()
                    job_title = job_title_element.text.strip()
                else:
                    job_title = "Title Not Found"
                
                company = 'C4iSolutions'
                
                # Location information is inside a span with the fas fa-map-marker-alt icon
                location_span = job.find('span', class_='text-secondary')
                if location_span:
                    location_icon = location_span.find('i', class_='fas fa-map-marker-alt')
                    if location_icon and location_icon.next_sibling:
                        location = location_icon.next_sibling.strip()
                    else:
                        location = location_span.text.strip()
                else:
                    location = "Location Not Found"
                
                print(f"Scraped job: {job_title} - {location}")
                
                new_data = pd.DataFrame({
                    'Link': [link_full], 
                    'Job Title': [job_title], 
                    'Job Classification': [job_classification],
                    'Location': [location], 
                    'Company': [company]})

                df = pd.concat([df, new_data], ignore_index=True)
                
            except Exception as e:
                print(f"Error scraping job: {e}")

        # Look for "Load More" button and click it if found
        try:
            # Try first with class 'btn-'
            load_more_buttons = driver.find_elements(By.CLASS_NAME, 'btn-')
            
            # If not found, try with class 'btn btn-secondary btn-apply'
            if not load_more_buttons:
                load_more_buttons = driver.find_elements(By.CSS_SELECTOR, 'button.btn.btn-secondary.load-more')
            
            # If still not found, try with text content
            if not load_more_buttons:
                load_more_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Load More')]")
            
            if load_more_buttons:
                # Store current number of jobs for comparison
                current_job_count = len(driver.find_elements(By.CLASS_NAME, 'media'))
                
                # Click the button
                driver.execute_script("arguments[0].click();", load_more_buttons[0])
                print("Clicked 'Load More' button. Loading more jobs...")
                
                # Wait for new content to load (wait for job count to increase)
                try:
                    WebDriverWait(driver, 5).until(
                        lambda d: len(d.find_elements(By.CLASS_NAME, 'media')) > current_job_count
                    )
                    time.sleep(1)  # Additional wait to ensure all content is loaded
                except TimeoutException:
                    print("No new jobs loaded after clicking 'Load More'. Ending search.")
                    break
            else:
                print("No 'Load More' button found. All jobs loaded.")
                break
                
        except Exception as e:
            print(f"Error with 'Load More' button: {e}")
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
        df = scrape_job_data(driver)
        save_df_to_csv(df, output_dir)
    finally:
        driver.quit()