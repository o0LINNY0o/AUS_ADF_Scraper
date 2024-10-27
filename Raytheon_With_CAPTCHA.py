import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
from fake_useragent import UserAgent
from typing import Optional, List, Dict

class JobScraper:
    def __init__(self, output_dir: str = '.\\csv_files'):
        self.output_dir = output_dir
        self.driver = None
        self.jobs_data = []
        
    def configure_webdriver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument(f'user-agent={UserAgent().random}')
        
        service = ChromeService(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        stealth(self.driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        
        return self.driver

    def wait_for_element(self, selector: str, by: By = By.CSS_SELECTOR, timeout: int = 10) -> Optional[webdriver.remote.webelement.WebElement]:
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except TimeoutException:
            return None

    def extract_job_data(self, job_element) -> Dict:
        try:
            link = job_element.get('href', '')
            if not link.startswith('http'):
                link = 'https://careers.rtx.com' + link
                
            job_title = (job_element.get('data-ph-at-job-title-text', '') or 
                        job_element.select_one('.job-title span').text if job_element.select_one('.job-title span') else '').strip()
            
            location = (job_element.get('data-ph-at-job-location-text', '') or 
                       job_element.select_one('.job-location').text if job_element.select_one('.job-location') else '').strip()
            
            job_classification = (job_element.get('data-ph-at-job-category-text', '') or 
                                job_element.select_one('.job-category').text if job_element.select_one('.job-category') else '').strip()
            
            return {
                'Link': link,
                'Job Title': job_title,
                'Job Classification': job_classification,
                'Location': location,
                'Company': 'Raytheon'
            }
        except Exception as e:
            print(f"Error extracting job data: {e}")
            return None

    def check_next_button_exists(self) -> bool:
        """Check if the next button with specific data-ph-at-id exists"""
        try:
            next_button = self.driver.find_element(By.CSS_SELECTOR, "[data-ph-at-id='pagination-next-text']")
            return next_button.is_displayed() and next_button.is_enabled()
        except (NoSuchElementException, StaleElementReferenceException):
            return False

    def scrape_current_page(self) -> List[Dict]:
        """Scrape jobs from the current page"""
        page_jobs = []
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        jobs = (soup.find_all('a', {'data-ph-at-id': 'job-link'}) or 
               soup.find_all('a', {'ph-tevent': 'job_click'}) or 
               soup.select('.jobs-list-item a'))
        
        for job in jobs:
            job_data = self.extract_job_data(job)
            if job_data:
                page_jobs.append(job_data)
        
        return page_jobs

    def scrape_jobs(self) -> List[Dict]:
        url = 'https://careers.rtx.com/global/en/raytheon-australia-search-results'
        self.driver.get(url)
        time.sleep(3)  # Initial load wait
        
        page_num = 1
        while True:
            print(f"Scraping page {page_num}")
            
            # Wait for job listings to load
            if not self.wait_for_element("[data-ph-at-id='jobs-list']"):
                print("Failed to load jobs page")
                break
            
            # Scrape current page
            current_page_jobs = self.scrape_current_page()
            if current_page_jobs:
                self.jobs_data.extend(current_page_jobs)
                print(f"Found {len(current_page_jobs)} jobs on page {page_num}")
            else:
                print(f"No jobs found on page {page_num}")
            
            # Check if next button exists
            if not self.check_next_button_exists():
                print("Next button not found - reached last page")
                break
            
            try:
                # Click next button
                next_button = self.driver.find_element(By.CSS_SELECTOR, "[data-ph-at-id='pagination-next-text']")
                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", next_button)
                time.sleep(2)  # Wait for page load
                
                # Verify page changed
                page_num += 1
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
            except Exception as e:
                print(f"Error navigating to next page: {e}")
                break
        
        return self.jobs_data

    def save_results(self):
        if not self.jobs_data:
            print("No data to save")
            return
            
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        file_path = os.path.join(self.output_dir, f'Raytheon_job_data_{timestamp}.csv')
        
        df = pd.DataFrame(self.jobs_data)
        df.to_csv(file_path, index=False)
        print(f"Data saved to {file_path}")

    def run(self):
        try:
            self.configure_webdriver()
            self.scrape_jobs()
            self.save_results()
            print(f"Successfully scraped {len(self.jobs_data)} jobs")
        except Exception as e:
            print(f"Error during scraping: {e}")
        finally:
            if self.driver:
                self.driver.quit()

def main():
    scraper = JobScraper()
    scraper.run()

if __name__ == "__main__":
    main()