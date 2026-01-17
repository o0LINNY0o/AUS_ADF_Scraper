import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
import time

def configure_webdriver():
    options = webdriver.ChromeOptions()
    options.add_argument('--log-level=1')
    options.add_argument('--disable-blink-features=AutomationControlled')
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
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])

    url = 'https://ats.rippling.com/embed/droneshield/jobs?s=https%3A%2F%2Fwww.droneshield.com%2Fopen-positions&page=0&searchQuery=&workplaceType=&country=AU&state=&city='
    driver.get(url)
    print(f"Scraping {url}")
    
    time.sleep(3)
    
    # Check for iframes
    iframes = driver.find_elements(By.TAG_NAME, 'iframe')
    print(f"Found {len(iframes)} iframe(s) on the page")
    
    # Try to find the main content iframe (if it exists)
    switched_to_iframe = False
    for idx, iframe in enumerate(iframes):
        try:
            iframe_src = iframe.get_attribute('src')
            iframe_id = iframe.get_attribute('id')
            iframe_height = iframe.get_attribute('height')
            print(f"  Iframe {idx}: id='{iframe_id}', height='{iframe_height}', src='{iframe_src}'")
            
            # Skip the small hidden iframe
            if iframe_height == "1":
                continue
                
            # Switch to iframe if it looks like the main content
            if iframe_id or (iframe_src and 'job' in iframe_src.lower()):
                print(f"  Switching to iframe {idx}...")
                driver.switch_to.frame(iframe)
                switched_to_iframe = True
                time.sleep(2)
                break
        except Exception as e:
            print(f"  Error checking iframe {idx}: {e}")
    
    if not switched_to_iframe:
        print("No obvious content iframe found, staying in main document")
    
    current_page = 1

    while True:
        try:
            print(f"Waiting for job listings to load on page {current_page}...")
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'css-aapqz6'))
            )
            print("Job listings loaded!")
            
        except TimeoutException:
            print("Timeout waiting for job boxes.")
            
            # Save debug info
            page_source = driver.page_source
            with open('debug_page_source.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            print("Page source saved to debug_page_source.html")
            
            # If we're in an iframe, try switching back
            if switched_to_iframe:
                print("Switching back to main document...")
                driver.switch_to.default_content()
                switched_to_iframe = False
                continue
            
            break

        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'lxml')
        job_boxes = soup.find_all('div', class_='css-aapqz6')

        print(f"Found {len(job_boxes)} job boxes on page {current_page}")

        if not job_boxes:
            print("No jobs found on this page. Stopping.")
            break

        for idx, box in enumerate(job_boxes, 1):
            try:
                link_elem = box.find('a', class_='css-18gdonj')
                if not link_elem:
                    link_elem = box.find('a', href=True)
                
                if link_elem:
                    link_full = link_elem.get('href', '')
                    job_title = link_elem.text.strip()
                else:
                    print(f"  Job {idx}: Could not find link element")
                    continue

                company = 'DroneShield'

                dept_elem = box.find('span', {'data-icon': 'DEPARTMENTS_OUTLINE'})
                if dept_elem:
                    job_classification = dept_elem.find_next('p').text.strip()
                else:
                    job_classification = 'N/A'

                loc_elem = box.find('span', {'data-icon': 'LOCATION_OUTLINE'})
                if loc_elem:
                    location = loc_elem.find_next('p').text.strip()
                else:
                    location = 'N/A'

                new_data = pd.DataFrame({
                    'Link': [link_full],
                    'Job Title': [job_title],
                    'Job Classification': [job_classification],
                    'Location': [location],
                    'Company': [company]
                })

                df = pd.concat([df, new_data], ignore_index=True)
                print(f"  Scraped: {job_title} - {location}")
                
            except Exception as e:
                print(f"  Error scraping job {idx}: {e}")

        # Check for next page
        try:
            next_page_buttons = driver.find_elements(By.CSS_SELECTOR, 'a[aria-label="Next page"]')
            
            if not next_page_buttons:
                print("No next page button found. Stopping.")
                break
                
            next_page_button = next_page_buttons[0]
            tabindex = next_page_button.get_attribute('tabindex')
            
            if tabindex == "-1":
                print("Reached the last page (next button disabled). Stopping.")
                break
                
            print(f"Navigating to page {current_page + 1}...")
            driver.execute_script("arguments[0].click();", next_page_button)
            current_page += 1
            time.sleep(3)

        except NoSuchElementException:
            print("No next page found.")
            break
        except Exception as e:
            print(f"Error navigating to next page: {e}")
            break

    # Switch back to main content if we were in an iframe
    if switched_to_iframe:
        driver.switch_to.default_content()

    print(f"\nTotal jobs scraped: {len(df)}")
    return df

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'Droneshield_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")

if __name__ == "__main__":
    output_dir = '.\\csv_files'
    driver = configure_webdriver()
    
    try:
        df = scrape_job_data(driver)
        
        if not df.empty:
            save_df_to_csv(df, output_dir)
            print("\n" + "="*50)
            print(f"Successfully scraped {len(df)} jobs")
            print("="*50)
        else:
            print("\nNo jobs were scraped. Check debug_page_source.html for details.")
            
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("Browser closed.")