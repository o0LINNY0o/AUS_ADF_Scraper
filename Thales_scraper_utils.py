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

    url = 'https://careers.thalesgroup.com/global/en/australia-jobs'
    driver.get(url)
    print(f"Scraping {url}")

    last_page = False  # Initialize the last_page flag here

    while True:
        soup = BeautifulSoup(driver.page_source, 'lxml')
        job_boxes = soup.find_all('a', {'data-ph-at-id': 'job-link'})

        if not job_boxes:  # Check if no jobs are found on the current page
            break

        for box in job_boxes:
            try:
                link_full = box.get('href')

                job_title = box.get('data-ph-at-job-title-text', '')

                company = 'Thales'

                Job_Classification = box.get('data-ph-at-job-category-text', '')

                location = box.get('data-ph-at-job-location-text', '')

                new_data = pd.DataFrame({
                    'Link': [link_full],
                    'Job Title': [job_title],
                    'Job Classification': [Job_Classification],
                    'Location': [location],
                    'Company': [company] })

                df = pd.concat([df, new_data], ignore_index=True)

            except Exception as e:
                print(f"Error scraping job: {e}")

        if last_page:
            print("Finished scraping the last page. Stopping.")
            break

        # Find the next page link using absolute URL
        try:
            next_page_element = soup.find('a', {'aria-label': 'View next page'})
            if not next_page_element:
                print("No more pages to scrape. Stopping.")
                break  # No more pages to scrape

            next_page_url = next_page_element.get('href')

            # Check if the title attribute is "Last Page"
            if next_page_element.get('title') == 'Last Page':
                last_page = True  # Set the flag to indicate we're on the last page

            # Print the URL for debugging
            print(f"Next page URL: {next_page_url}")

            if next_page_url is None or not isinstance(next_page_url, str):
                print("Invalid URL. Skipping...")
                break  # Skip to the next iteration if the URL is invalid

            driver.get(next_page_url)

        except NoSuchElementException as e:
            print(f"No next page found: {e}")
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
    file_path = os.path.join(output_dir, 'Thales_job_data.csv')

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
