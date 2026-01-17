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

    url = 'https://www.rohde-schwarz.com/au/career/jobs/career-jobboard_251573.html?term=&filter%5B_raw.country%5D%5B%5D=Australia#jobBoard'
    driver.get(url)
    print(f"Scraping {url}")

    # Wait for the page to load
    driver.implicitly_wait(10)
    
    soup = BeautifulSoup(driver.page_source, 'lxml')
    job_lists = soup.find_all('div', {'class': 'accordion-table-list'})

    if not job_lists:
        print("No jobs found")
        return df

    for job_list in job_lists:
        try:
            # Find job title and link
            title_div = job_list.find('div', {'class': 'accordion-table-list-item-title'})
            if title_div:
                link_element = title_div.find('a', {'class': 'accordion-table-list-item-title-link'})
                if link_element:
                    job_title = link_element.text.strip()
                    link = 'https://www.rohde-schwarz.com' + link_element['href']
                
            # Find job classification (Functional area)
            classification_div = job_list.find('div', {'class': 'column-3'})
            if classification_div:
                classification_info = classification_div.find('div', {'class': 'accordion-table-list-item-info'})
                job_classification = classification_info.text.strip() if classification_info else ''

            # Find location (combining City/region and Location)
            location_div = job_list.find('div', {'class': 'column-5'})
            city_div = job_list.find('div', {'class': 'column-6'})
            
            location_info = ''
            if location_div and city_div:
                country = location_div.find('div', {'class': 'accordion-table-list-item-info'})
                city = city_div.find('div', {'class': 'accordion-table-list-item-info'})
                location_info = f"{city.text.strip()}, {country.text.strip()}" if city and country else ''

            new_data = pd.DataFrame({
                'Link': [link],
                'Job Title': [job_title],
                'Job Classification': [job_classification],
                'Location': [location_info],
                'Company': ['R&S']
            })

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
    file_path = os.path.join(output_dir, 'RS_job_data.csv')

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
