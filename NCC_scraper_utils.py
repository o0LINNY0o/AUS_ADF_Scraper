import os
import pandas as pd
from bs4 import BeautifulSoup
from seleniumbase import SB
import time

def scrape_job_data():
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])

    url = 'https://newcastle.nsw.gov.au/about-us/careers/employment-opportunities'
    
    with SB(uc=True, headless=True) as sb:
        sb.open(url)
        print(f"Scraping {url}")
        
        # Wait for page to load
        time.sleep(3)
        
        # Switch to the iframe containing the job listings
        try:
            iframe_selector = "#newcastle_iframe"
            sb.wait_for_element(iframe_selector, timeout=10)
            sb.switch_to_frame(iframe_selector)
            print("Successfully switched to iframe")
            
            # Wait for jobs to load inside iframe
            time.sleep(3)
            
        except Exception as e:
            print(f"Error switching to iframe: {e}")
            print("Trying alternative iframe selectors...")
            
            # Try alternative iframe selectors
            alternative_selectors = [
                'iframe[src*="newcastle.applynow.net.au"]',
                'iframe[title*="job opportunities"]',
                'iframe[title*="Job opportunities"]',
                'iframe[id*="newcastle"]'
            ]
            
            iframe_found = False
            for selector in alternative_selectors:
                try:
                    sb.wait_for_element(selector, timeout=5)
                    sb.switch_to_frame(selector)
                    print(f"Successfully switched to iframe using selector: {selector}")
                    iframe_found = True
                    time.sleep(3)
                    break
                except:
                    continue
            
            if not iframe_found:
                print("Could not find iframe, proceeding with main page...")
        
        page_num = 1
        
        while True:
            print(f"Scraping page {page_num}")
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(sb.get_page_source(), 'html.parser')
            
            # Find job containers using the structure from your HTML
            job_containers = soup.find_all('div', class_='jobblock block')
            
            if not job_containers:
                print("No job containers found on this page")
                break
            
            print(f"Found {len(job_containers)} jobs on page {page_num}")
            
            for container in job_containers:
                try:
                    # Extract job title and link
                    title_link = container.find('a', class_='job_title')
                    if not title_link:
                        continue
                        
                    job_title = title_link.get_text(strip=True)
                    link_full = title_link.get('href', '')
                    
                    # Extract job ID (reference) from span with class 'jobid'
                    job_id_span = container.find('span', class_='jobid')
                    job_classification = job_id_span.get_text(strip=True) if job_id_span else ""
                    
                    # Extract location from span with class 'location'
                    location_span = container.find('span', class_='location')
                    location = location_span.get_text(strip=True) if location_span else ""
                    
                    # Alternative method: extract from data attributes if spans are not found
                    if not job_classification:
                        job_classification = container.get('data-reference', '')
                    
                    if not location:
                        location = container.get('data-location', '')
                    
                    company = 'Newcastle City Council'
                    
                    new_data = pd.DataFrame({
                        'Link': [link_full],
                        'Job Title': [job_title],
                        'Job Classification': [job_classification],
                        'Location': [location],
                        'Company': [company]
                    })
                    
                    df = pd.concat([df, new_data], ignore_index=True)
                    print(f"Scraped: {job_title} - {job_classification} - {location}")
                    
                except Exception as e:
                    print(f"Error scraping job container: {e}")
                    continue
            
            # Check for pagination - look inside iframe content
            try:
                # Try to stay within iframe context for pagination
                next_button = None
                
                # Look for common pagination patterns within iframe
                pagination_selectors = [
                    'a[aria-label="Next page"]',
                    'a[aria-label="View next page"]',
                    '.pagination a.next',
                    '.pager a.next',
                    'a.next',
                    '.next-page',
                    '[data-page-next]'
                ]
                
                for selector in pagination_selectors:
                    try:
                        next_button = sb.find_element(selector, timeout=2)
                        if next_button and next_button.is_enabled():
                            break
                    except:
                        continue
                
                if next_button and next_button.is_enabled():
                    # Click the next button instead of navigating to URL (since we're in iframe)
                    try:
                        sb.click(next_button)
                        time.sleep(3)
                        page_num += 1
                    except Exception as e:
                        print(f"Error clicking next button: {e}")
                        break
                else:
                    print("No next page button found or enabled")
                    break
                    
            except Exception as e:
                print(f"No more pages")
                break
    
    return df

def save_df_to_csv(df, output_dir):
    # Ensure the directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Define the file path for the CSV
    file_path = os.path.join(output_dir, 'NCC_job_data.csv')

    # Save the DataFrame to a CSV file
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")
    
# Create the .csv_files directory if it doesn't exist
output_dir = '.\\csv_files'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Main execution
if __name__ == "__main__":
    try:
        df = scrape_job_data()
        save_df_to_csv(df, output_dir)
    except Exception as e:
        print(f"Error during execution: {e}")