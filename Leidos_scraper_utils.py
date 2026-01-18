import os
import pandas as pd
from seleniumbase import SB
import time

def scrape_page_jobs(sb):
    """Scrape all jobs from the current page."""
    jobs_data = []
    
    try:
        job_items = sb.find_elements('div.jobs-section__item')
        print(f"Found {len(job_items)} job listings on this page")
        
        for job in job_items:
            try:
                # Extract job title and link
                title_element = job.find_element('css selector', 'div.large-4 a')
                job_title = title_element.text.strip()
                link = title_element.get_attribute('href')
                
                # Extract location
                try:
                    location_element = job.find_element('css selector', 'div.large-3.columns')
                    location = location_element.text.strip()
                    # Remove "Location: " prefix if present
                    location = location.replace('Location:', '').strip()
                except:
                    location = 'Not specified'
                
                # Extract job classification (clearance level)
                try:
                    clearance_elements = job.find_elements('css selector', 'div.large-3.columns')
                    if len(clearance_elements) >= 2:
                        job_classification = clearance_elements[1].text.strip()
                        job_classification = job_classification.replace('Clearance:', '').strip()
                    else:
                        job_classification = 'Not specified'
                except:
                    job_classification = 'Not specified'
                
                jobs_data.append({
                    'Link': link,
                    'Job Title': job_title,
                    'Job Classification': job_classification,
                    'Location': location,
                    'Company': 'Leidos'
                })
                
                print(f"Scraped: {job_title} - {location}")
                
            except Exception as e:
                print(f"Error scraping individual job: {e}")
                continue
                
    except Exception as e:
        print(f"Error finding job listings: {e}")
    
    return jobs_data

def scrape_job_data(sb):
    all_jobs_data = []
    
    url = 'https://auscareers.leidos.com/search/jobs'
    sb.open(url)
    print(f"Scraping {url}")
    
    # Wait for the page to load
    sb.wait_for_element('div.jobs-section__item', timeout=15)
    
    # Add random delay to appear more human-like
    sb.sleep(2)
    
    page_num = 1
    
    while True:
        print(f"\n--- Scraping Page {page_num} ---")
        
        # Scrape jobs from current page
        jobs_data = scrape_page_jobs(sb)
        all_jobs_data.extend(jobs_data)
        print(f"Total jobs scraped so far: {len(all_jobs_data)}")
        
        # Look for next page button
        try:
            if sb.is_element_visible('a.next_page'):
                next_button = sb.find_element('a.next_page')
                
                # Check if next button is disabled
                if 'disabled' in next_button.get_attribute('class'):
                    print("No more pages to scrape")
                    break
                
                # Human-like behavior: scroll around a bit before clicking
                sb.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                sb.sleep(1)
                
                # Scroll to next button and click
                print(f"Moving to page {page_num + 1}...")
                sb.scroll_to('a.next_page')
                sb.sleep(1)
                
                # Click using SeleniumBase method (handles Cloudflare better)
                sb.click('a.next_page')
                
                # Wait for new page to load
                sb.sleep(3)
                sb.wait_for_element('div.jobs-section__item', timeout=15)
                
                # Additional wait to ensure page fully loads
                sb.sleep(2)
                
                page_num += 1
            else:
                print("No next page button found - finished scraping")
                break
                
        except Exception as e:
            print(f"Error navigating to next page: {e}")
            break
    
    return pd.DataFrame(all_jobs_data)

def save_df_to_csv(df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, 'Leidos_job_data.csv')
    
    try:
        df.to_csv(file_path, index=False)
        print(f"\nData saved to {file_path}")
        print(f"Total jobs scraped: {len(df)}")
    except Exception as e:
        print(f"Error saving data to CSV: {e}")

# Main execution
if __name__ == "__main__":
    output_dir = '.\\csv_files'
    
    # Use SeleniumBase with UC mode (undetected) to bypass Cloudflare
    with SB(uc=True, headless=True) as sb:
        try:
            df = scrape_job_data(sb)
            
            if not df.empty:
                save_df_to_csv(df, output_dir)
            else:
                print("No jobs were scraped")
                
        except Exception as e:
            print(f"Error in main execution: {e}")
