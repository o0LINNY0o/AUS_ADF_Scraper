import os
import pandas as pd
from bs4 import BeautifulSoup
from seleniumbase import SB
import time

def scrape_job_data():
    df = pd.DataFrame(columns=['Link', 'Job Title', 'Job Classification', 'Location', 'Company'])

    url = 'https://clientapps.jobadder.com/40037/kongsberg-defence-australia'
    
    with SB(uc=True, headless=True) as sb:
        sb.open(url)
        print(f"Scraping {url}")
        
        # Wait for page to load
        time.sleep(3)
        
        page_num = 1
        
        while True:
            print(f"Scraping page {page_num}")
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(sb.get_page_source(), 'html.parser')
            
            # Find job containers using the structure from your HTML
            job_containers = soup.find_all('div', class_='pricing-item price_item2')
            
            if not job_containers:
                print("No job containers found on this page")
                break
            
            print(f"Found {len(job_containers)} jobs on page {page_num}")
            
            for container in job_containers:
                try:
                    # Extract job title and link
                    title_link = container.find('h2').find('a', class_='viewjob')
                    if not title_link:
                        continue
                        
                    job_title = title_link.get_text(strip=True)
                    link_relative = title_link.get('href')
                    link_full = f"https://clientapps.jobadder.com{link_relative}" if link_relative else ""
                    
                    # Extract job classification and location from the list items
                    list_items = container.find('ul', class_='list').find_all('li')
                    
                    # Initialize variables
                    job_classification = ""
                    location = ""
                    
                    # Parse the list items to extract classification and location
                    # Based on your example: Engineering, Systems, NSW Other, Permanent / Full Time
                    if len(list_items) >= 3:
                        # Second item is typically the specific classification
                        job_classification = list_items[1].get_text(strip=True)
                        # Third item is typically the location
                        location = list_items[2].get_text(strip=True)
                    
                    company = 'Kongsberg'
                    
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
            
            # Check for next page
            try:
                # Look for pagination elements
                next_button = sb.find_element('a[aria-label="View next page"]', timeout=2)
                if next_button and next_button.is_enabled():
                    # Check if it's the last page
                    if next_button.get_attribute('title') == 'Last Page':
                        print("Reached last page")
                        break
                    
                    next_url = next_button.get_attribute('href')
                    if next_url:
                        sb.open(next_url)
                        time.sleep(3)
                        page_num += 1
                    else:
                        break
                else:
                    print("No next page button found")
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
    file_path = os.path.join(output_dir, 'Kongsberg_job_data.csv')

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