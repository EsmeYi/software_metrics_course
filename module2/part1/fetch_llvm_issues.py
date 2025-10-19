import os
import requests
import csv
import time
import json
import sys
from datetime import datetime, timedelta, timezone

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

def load_config(config_path='config.json'):
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found.")
        return None
    with open(config_path, 'r') as f:
        return json.load(f).get("fetch_settings")

def fetch_llvm_issues(config):
    if not config:
        print("Error: Fetch settings ('fetch_settings') not found in config.json.")
        return

    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    repo = config['github_repo']
    keywords = config['search_keywords']
    state = config.get('issue_state', 'all')
    start_date = config.get('created_after_date')
    output_file = config['output_csv_file']
    
    state_query = f"is:{state}" if state in ['open', 'closed'] else ""
    date_query = f"created:>={start_date}" if start_date else ""
    query = f"repo:{repo} is:issue {state_query} {date_query} {keywords}"
    
    params = {"q": query.strip(), "per_page": 100}
    issues_found = []
    page = 1

    print(f"--- Starting data fetch from GitHub ---")
    print(f"Constructed Query: {params['q']}")

    while True:
        if len(issues_found) >= 1000:
            print("\nInfo: Reached GitHub API's 1000-result limit.")
            break
        params['page'] = page
        print(f"Fetching page {page}...")
        try:
            response = requests.get("https://api.github.com/search/issues", headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            issues_on_this_page = data.get('items', [])
            total_count = data.get('total_count', 0)
            if not issues_on_this_page:
                break
            issues_found.extend(issues_on_this_page)
            if len(issues_found) >= total_count:
                break
            page += 1
            time.sleep(1)
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            break
            
    if not issues_found:
        print("\nNo issues were fetched.")
        return

    print(f"\nFound a total of {len(issues_found)} unique issues.")
    issues_found.sort(key=lambda issue: issue['created_at'])
    print(f"Writing sorted data to {output_file}...")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['bug_id', 'creation_date', 'updated_at', 'closed_at', 'status', 'priority', 'component', 'severity', 'reported_by', 'defect_type'])
        
        now_utc = datetime.now(timezone.utc)
        one_year_ago = now_utc - timedelta(days=365)

        for issue in issues_found:
            creation_dt = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
            
            priority = 'Medium'
            if issue['state'] == 'open' and creation_dt < one_year_ago:
                priority = 'Low'

            writer.writerow([
                f"GH-{issue['number']}",
                issue['created_at'][:19], # Truncate to seconds for consistency
                issue['updated_at'][:19], # New: Capture updated_at
                issue['closed_at'][:19] if issue['closed_at'] else '',
                issue['state'],
                priority, 'Unknown', 'Major',
                f"Upstream LLVM ({issue['user']['login']})",
                'Regression'
            ])
            
    print("Write complete! New logic has been applied.")

if __name__ == "__main__":
    fetch_config = load_config()
    if fetch_config:
        fetch_llvm_issues(fetch_config)
