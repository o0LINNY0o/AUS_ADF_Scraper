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

def configure_webdriver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument('--log-level=1')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
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

def scrape_job_data(driver, Job_Classification, location):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])

    url = 'https://jobs.babcockinternational.com/go/Australasia/4733701/'
    driver.get(url)
    print(f"Scraping {url}")

    while True:
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'data-row'))
            )
        except TimeoutException:
            print("Timeout waiting for page to load. Stopping.")
            break

        soup = BeautifulSoup(driver.page_source, 'lxml')
        job_boxes = soup.find_all('tr', {'class': 'data-row'})

        if not job_boxes:  # Check if no jobs are found on the current page
            print("No jobs found on this page. Stopping.")
            break

        for box in job_boxes:
            try:
                link_tag = box.find('a', {'class': 'jobTitle-link'})
                link = link_tag.get('href')
                link_full = 'https://jobs.babcockinternational.com' + link

                job_title = link_tag.text.strip()
                print(f"Scraped job: {job_title} - {location}")

                company = 'Babcock'

                Job_Classification = box.get('data-ph-at-job-category-text', '')

                location_tag = box.find('span', {'class': 'jobLocation'})
                if location_tag:
                    # Remove the <small> tag content
                    small_tag = location_tag.find('small')
                    if small_tag:
                        small_tag.decompose()  # Remove the <small> tag
                    location = location_tag.text.strip()
                else:
                    location = ''

                new_data = pd.DataFrame({
                    'Link': [link_full],
                    'Job Title': [job_title],
                    'Job Classification': [Job_Classification],
                    'Location': [location],
                    'Company': [company] })

                df = pd.concat([df, new_data], ignore_index=True)

            except Exception as e:
                print(f"Error scraping job: {e}")

        # Check the pagination label to determine the current and total page numbers
        try:
            pagination_label = driver.find_element(By.CSS_SELECTOR, 'span.srHelp')
            pagination_text = pagination_label.text.strip()
            print(f"Pagination text: {pagination_text}")
            parts = pagination_text.split()
            current_page = int(parts[-3])
            total_pages = int(parts[-1])
            if current_page >= total_pages:
                print("Reached the last page. Stopping.")
                break
        except (NoSuchElementException, ValueError, IndexError) as e:
            print(f"Pagination label not found or invalid: {e}. Stopping.")
            break

        # Find the last page link using the pagination links
        try:
            last_page_element = driver.find_element(By.CSS_SELECTOR, 'a.paginationItemLast[title="Last Page"]')
            if last_page_element:
                last_page_url = last_page_element.get_attribute('href')
                if last_page_url:
                    driver.get(last_page_url)
                    print(f"Navigating to the last page: {last_page_url}")
                else:
                    print("Last page URL is invalid. Stopping.")
                    break
            else:
                print("Last page element not found. Stopping.")
                break

        except NoSuchElementException:
            print("No last page found. Stopping.")
            break

    return df

# Create the .csv_files directory if it doesn't exist
output_dir = '.\\csv_files'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def save_df_to_csv(df, output_dir):
    # Ensure the directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Define the file path for the CSV
    file_path = os.path.join(output_dir, 'Babcock_job_data.csv')

    # Save the DataFrame to a CSV file
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
