import os
import pandas as pd
from seleniumbase import SB

def scrape_maitland_council_jobs():
    """
    Scrape job listings from Maitland Council career site using SeleniumBase
    """
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])
    
    url = 'https://maitlandcouncil.csod.com/ux/ats/careersite/1/home?c=maitlandcouncil&source=seek_oz'
    
    with SB(uc=True, headless=True) as sb:
        print(f"Scraping {url}")
        sb.open(url)
        
        # Wait for job listings to load
        sb.sleep(3)
        
        page_number = 1
        
        while True:
            print(f"Scraping page {page_number}...")
            
            # Find all potential job listing containers
            job_containers = sb.find_elements('div.p-panel.p-bg-white')
            
            if not job_containers:
                print("No job listings found on this page.")
                break
            
            print(f"Found {len(job_containers)} potential containers on page {page_number}")
            
            for container in job_containers:
                try:
                    # Check if the title element exists inside this container
                    title_links = container.find_elements('css selector', 'a[data-tag="displayJobTitle"]')
                    
                    if not title_links:
                        # Skip this container silently (likely 'Join Talent Community' box)
                        continue
                        
                    # Get the first link found
                    title_link = title_links[0]
                    
                    # Extract Job Title Text
                    job_title_elem = title_link.find_element('css selector', 'p[data-tag]')
                    job_title = job_title_elem.text.strip()
                    
                    # Get Link
                    link_href = title_link.get_attribute('href')
                    
                    # Construct absolute URL
                    if link_href and not link_href.startswith('http'):
                        link_full = 'https://maitlandcouncil.tagmax.com.au' + link_href
                    else:
                        link_full = link_href
                    
                    # Set Location to Newcastle (Hardcoded as requested)
                    location = 'Newcastle'
                    
                    # Company is always Maitland Council
                    company = 'Maitland Council'
                    
                    # Job classification
                    job_classification = 'Not specified'
                    
                    # Print status
                    print(f"Scraped: {job_title} - {location}")
                    
                    # Create new row
                    new_data = pd.DataFrame({
                        'Link': [link_full],
                        'Job Title': [job_title],
                        'Job Classification': [job_classification],
                        'Location': [location],
                        'Company': [company]
                    })
                    
                    df = pd.concat([df, new_data], ignore_index=True)
                    
                except Exception as e:
                    print(f"Error scraping a specific container: {e}")
                    continue
            
            # Check for next page button
            try:
                next_button = sb.find_element('button[aria-label*="next" i], a[aria-label*="next" i]', timeout=2)
                
                if next_button.get_attribute('disabled') or 'disabled' in next_button.get_attribute('class'):
                    print("Reached last page.")
                    break
                
                sb.click(next_button)
                sb.sleep(2)
                page_number += 1
                
            except Exception as e:
                print(f"No more pages or error navigating: {e}")
                break
    
    return df


def save_df_to_csv(df, output_dir='./csv_files'):
    """
    Save DataFrame to CSV file
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    file_path = os.path.join(output_dir, 'Maitland_Council_job_data.csv')
    df.to_csv(file_path, index=False)
    print(f"\nData saved to {file_path}")
    print(f"Total jobs scraped: {len(df)}")


# Main execution
if __name__ == "__main__":
    print("Starting Maitland Council job scraper...")
    df = scrape_maitland_council_jobs()
    
    if not df.empty:
        save_df_to_csv(df)
    else:
        print("No jobs found.")