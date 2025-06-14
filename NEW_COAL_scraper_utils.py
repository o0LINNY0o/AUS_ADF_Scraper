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

def scrape_job_data(driver):
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])

    url = 'https://ncig.com.au/who-we-are/recruitment/'
    driver.get(url)
    print(f"Scraping {url}")

    soup = BeautifulSoup(driver.page_source, 'lxml')
    job_links = soup.select('div.acf-flex-row.wysiwyg a[href]')

    for link in job_links:
        try:
            job_title = link.text.strip()
            link_full = link.get('href')

            # Exclude unwanted phrases and links
            if ("Talent Community" in job_title or
                "Join our" in job_title or
                "Employment Management Approach" in job_title or
                "LinkedIn" in job_title or
                "ncig.com.au/policies-reports/management-approaches/employment" in link_full or
                "linkedin.com/company/newcastle-coal-infrastructure-group-pty-ltd" in link_full):
                continue

            company = 'NCIG'
            job_classification = 'N/A'
            location = 'Newcastle'

            new_data = pd.DataFrame({
                'Link': [link_full],
                'Job Title': [job_title],
                'Job Classification': [job_classification],
                'Location': [location],
                'Company': [company] })

            df = pd.concat([df, new_data], ignore_index=True)

        except Exception as e:
            print(f"Error scraping job: {e}")

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
    file_path = os.path.join(output_dir, 'NCIG_job_data.csv')

    # Save the DataFrame to a CSV file
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
