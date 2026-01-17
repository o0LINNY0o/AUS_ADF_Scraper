import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
import logging
import time
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# --- Configure logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Thread-safe session with connection pooling
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
})

def construct_page_url(base_url, page_number):
    """Construct URL for a specific page number - optimized"""
    if page_number == 1:
        return base_url
    
    # Simple string replacement for pagination
    if 'page=' in base_url:
        return re.sub(r'page=\d+', f'page={page_number}', base_url)
    else:
        connector = '&' if '?' in base_url else '?'
        return f"{base_url}{connector}page={page_number}"

def get_max_page_number(soup):
    """Extract maximum page number - optimized with regex"""
    try:
        # Find pagination text and extract numbers with regex
        pagination_text = soup.find('nav', {'role': 'navigation', 'aria-label': 'pagination'})
        if not pagination_text:
            return 1
        
        # Extract all numbers from pagination area
        numbers = re.findall(r'\b(\d+)\b', pagination_text.get_text())
        page_numbers = [int(n) for n in numbers if int(n) <= 50]  # Reasonable upper limit
        
        if page_numbers:
            max_page = max(page_numbers)
            logger.info(f"Found maximum page number: {max_page}")
            return max_page
        return 1
        
    except Exception as e:
        logger.error(f"Error extracting max page number: {e}")
        return 1

def scrape_jobs_from_page(html_content, base_url):
    """Extract job data from a single page - optimized parsing"""
    # Use lxml parser for speed if available, fallback to html.parser
    try:
        soup = BeautifulSoup(html_content, 'lxml')
    except:
        soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find job containers with more specific selector
    job_containers = soup.select('div.gap-4.md\\:gap-6.flex.flex-col div.flex.gap-0\\.5.group')
    
    if not job_containers:
        # Fallback to original method
        parent_container = soup.find('div', class_='gap-4 md:gap-6 flex flex-col')
        if parent_container:
            job_containers = parent_container.find_all('div', class_='flex gap-0.5 group')
    
    if not job_containers:
        logger.warning("No job containers found on this page")
        return [], [], [], [], []
    
    # Pre-allocate lists for better performance
    count = len(job_containers)
    links = ['N/A'] * count
    job_titles = ['N/A'] * count
    job_classifications = ['N/A'] * count
    locations = ['N/A'] * count
    companies = ['N/A'] * count
    
    logger.debug(f"Processing {count} job containers")
    
    # Process all containers in one loop
    for i, container in enumerate(job_containers):
        
        # --- Extract Link (optimized) ---
        link_tag = container.find('a', href=True)
        if link_tag and link_tag.get('href'):
            links[i] = urljoin(base_url, link_tag['href'])
        
        # --- Extract Job Title (optimized) ---
        title_div = container.find('div', class_='text-sm font-bold md:text-xl mb-2')
        if title_div:
            # Faster text extraction
            title_text = title_div.get_text(strip=True)
            if title_text:
                job_titles[i] = title_text.replace('\xa0', ' ')
        
        # --- Extract Location and Company (optimized) ---
        loc_comp_div = container.find('div', class_='flex flex-wrap mr-6')
        if loc_comp_div:
            # Get text once and split
            text_content = loc_comp_div.get_text(separator='|', strip=True)
            if text_content:
                parts = [p.strip() for p in text_content.split('|') if p.strip()]
                
                if len(parts) >= 2:
                    company_raw = parts[0]
                    locations[i] = parts[1]
                    # Quick company name extraction
                    companies[i] = "Rheinmetall" if "Rheinmetall" in company_raw else company_raw
                elif len(parts) == 1:
                    company_raw = parts[0]
                    companies[i] = "Rheinmetall" if "Rheinmetall" in company_raw else company_raw
    
    return links, job_titles, job_classifications, locations, companies

def fetch_page(page_info):
    """Fetch a single page - for threading"""
    page_num, url, max_pages = page_info
    
    try:
        logger.info(f"Fetching page {page_num}/{max_pages}")
        response = session.get(url, timeout=10)
        response.raise_for_status()
        return page_num, response.text, None
    except Exception as e:
        logger.error(f"Error fetching page {page_num}: {e}")
        return page_num, None, str(e)

def save_df_to_csv(df, output_dir):
    """Save DataFrame to CSV file with proper directory handling"""
    # Ensure the directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Define the file path for the CSV
    file_path = os.path.join(output_dir, 'Rheinmetall_job_data.csv')

    # Save the DataFrame to a CSV file
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")
    logger.info(f"✅ Data saved to {file_path}")
    return file_path

def main():
    """Main function with parallel processing"""
    base_url_site = "https://www.rheinmetall.com"
    initial_url = "https://www.rheinmetall.com/en/career/vacancies?9dc11c304b4c06c2f71c48cc6574e7e5term=&9dc11c304b4c06c2f71c48cc6574e7e5filter=%257B%2522countries%2522%253A%255B%2522Australia%2522%255D%257D"
    
    # Create the .csv_files directory if it doesn't exist
    output_dir = '.\\csv_files'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Combined data storage
    all_data = {
        'links': [],
        'titles': [],
        'classifications': [],
        'locations': [],
        'companies': []
    }
    
    max_pages = 1  # Initialize with default value
    
    try:
        # 1. Fetch first page to get total pages
        logger.info("Fetching initial page to determine pagination...")
        response = session.get(initial_url, timeout=15)
        response.raise_for_status()
        
        # Parse for max pages
        try:
            soup = BeautifulSoup(response.text, 'lxml')
        except:
            soup = BeautifulSoup(response.text, 'html.parser')
            
        max_pages = get_max_page_number(soup)
        logger.info(f"Total pages to scrape: {max_pages}")
        
        # 2. Process first page immediately
        links, titles, classifications, locations, companies = scrape_jobs_from_page(response.text, base_url_site)
        all_data['links'].extend(links)
        all_data['titles'].extend(titles)
        all_data['classifications'].extend(classifications)
        all_data['locations'].extend(locations)
        all_data['companies'].extend(companies)
        logger.info(f"Page 1: Found {len(links)} jobs")
        
        # 3. Fetch remaining pages in parallel (if any)
        if max_pages > 1:
            # Prepare page info for threading
            page_tasks = []
            for page_num in range(2, max_pages + 1):
                page_url = construct_page_url(initial_url, page_num)
                page_tasks.append((page_num, page_url, max_pages))
            
            # Use ThreadPoolExecutor for parallel requests
            max_workers = min(4, len(page_tasks))  # Limit concurrent requests
            logger.info(f"Fetching {len(page_tasks)} pages with {max_workers} threads...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_page = {executor.submit(fetch_page, task): task for task in page_tasks}
                
                # Process completed pages
                for future in as_completed(future_to_page):
                    page_num, html_content, error = future.result()
                    
                    if error:
                        logger.warning(f"Skipping page {page_num} due to error: {error}")
                        continue
                    
                    if html_content:
                        # Extract jobs from this page
                        links, titles, classifications, locations, companies = scrape_jobs_from_page(html_content, base_url_site)
                        
                        # Thread-safe data aggregation
                        all_data['links'].extend(links)
                        all_data['titles'].extend(titles)
                        all_data['classifications'].extend(classifications)
                        all_data['locations'].extend(locations)
                        all_data['companies'].extend(companies)
                        
                        logger.info(f"Page {page_num}: Found {len(links)} jobs")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error with initial request: {e}")
        # Fallback to file
        try:
            with open('Pasted_Text_1753270643426.txt', 'r', encoding='utf-8') as f:
                html_content = f.read()
            logger.info("Using fallback file content")
            
            links, titles, classifications, locations, companies = scrape_jobs_from_page(html_content, base_url_site)
            all_data['links'].extend(links)
            all_data['titles'].extend(titles)
            all_data['classifications'].extend(classifications)
            all_data['locations'].extend(locations)
            all_data['companies'].extend(companies)
            
        except FileNotFoundError:
            logger.error("No fallback file found. Exiting.")
            return
    
    # 4. Create DataFrame and clean data
    if not all_data['links']:
        logger.error("No job data found!")
        return
    
    df = pd.DataFrame({
        'Link': all_data['links'],
        'Job Title': all_data['titles'],
        'Job Classification': all_data['classifications'],
        'Location': all_data['locations'],
        'Company': all_data['companies']
    })
    
    # Remove duplicates efficiently
    initial_count = len(df)
    df = df.drop_duplicates(subset=['Job Title', 'Location'], keep='first')
    final_count = len(df)
    
    if initial_count != final_count:
        logger.info(f"Removed {initial_count - final_count} duplicates")
    
    # 5. Save to CSV using the proper function
    if final_count > 0:
        saved_file = save_df_to_csv(df, output_dir)
    
    # 6. Output results
    print(f"\n{'='*80}")
    print(f"RHEINMETALL JOBS SCRAPER RESULTS")
    print(f"{'='*80}")
    print(f"Total unique jobs found: {final_count}")
    print(f"Pages scraped: {max_pages}")
    print(f"{'='*80}")
    
    if final_count > 0:
        print(df.to_string(index=False))
        
        # 7. Summary stats
        print(f"\n--- SUMMARY STATISTICS ---")
        print(f"🎯 Total Jobs: {final_count}")
        print(f"📍 Locations: {len(df['Location'].unique())}")
        print(f"🏢 Companies: {len(df['Company'].unique())}")
        print(f"📄 Pages Processed: {max_pages}")
        print(f"💾 Saved to: {saved_file}")
        
        # Location breakdown
        location_counts = df['Location'].value_counts()
        print(f"\n📊 Jobs by Location:")
        for location, count in location_counts.items():
            print(f"   {location}: {count} jobs")
    else:
        print("No jobs found to display.")

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"\n⏱️  Total execution time: {end_time - start_time:.2f} seconds")