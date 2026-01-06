import os
import csv
import re
import subprocess
import requests
import math
import time
import lizard  # pip install lizard
from datetime import datetime, timezone, timedelta

# --- Configuration ---
REPO_PATH = "./llvm-project"
OUTPUT_FILE = "daily_metrics.csv"
GITHUB_REPO = "llvm/llvm-project"
TOKEN = os.getenv('GITHUB_TOKEN')
SCHEDULE_HOUR = 8
TEST_MODE = False

# --- Helper: Get Anchor Date ---
def get_anchor_date(repo_path):
    try:
        cmd = ['git', '-C', repo_path, 'log', '-1', '--format=%cI']
        result = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
        if result.returncode == 0 and result.stdout.strip():
            iso_str = result.stdout.strip()
            return datetime.fromisoformat(iso_str).astimezone(timezone.utc)
    except: pass
    return datetime.now(timezone.utc)

def update_repo(repo_path):
    print(f"  [Git] Pulling latest changes in {repo_path}...")
    if not os.path.exists(repo_path): return
    try:
        subprocess.run(['git', '-C', repo_path, 'pull'], capture_output=True)
    except: pass

# --- 1. Advanced Git Metrics (Entropy, Churn, Authors) ---
def calculate_shannon_entropy(file_changes):
    """
    Calculates Shannon Entropy for a single commit.
    Source: Hassan (2009), "Predicting faults using the complexity of code changes"
    """
    total_change = sum(file_changes)
    if total_change == 0: return 0
    entropy = 0
    for change in file_changes:
        p = change / total_change
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy

def get_git_metrics(repo_path, anchor_date):
    print(f"  [Git] Analyzing log relative to {anchor_date.date()}...")
    since = (anchor_date - timedelta(days=1)).strftime('%Y-%m-%d')
    until = (anchor_date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Format: Hash|Author|NumStat
    cmd = ['git', '-C', repo_path, 'log', f'--since={since}', f'--until={until}', '--numstat', '--pretty=format:COMMIT_META|%H|%ae']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
    except: return 0, 0, 0

    lines = result.stdout.splitlines()
    authors = set()
    total_churn = 0
    
    # Entropy Calculation Variables
    commit_changes = [] # List of list of file changes per commit
    current_commit_files = []
    
    for line in lines:
        if line.startswith('COMMIT_META'):
            # New commit start: save previous commit data
            if current_commit_files:
                commit_changes.append(current_commit_files)
            current_commit_files = [] # Reset for new commit
            
            parts = line.split('|')
            if len(parts) >= 3:
                authors.add(parts[2])
        elif line.strip():
            # File stat line: "added  deleted  filename"
            parts = line.split()
            if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
                lines_changed = int(parts[0]) + int(parts[1])
                total_churn += lines_changed
                current_commit_files.append(lines_changed)
    
    # Don't forget the last commit
    if current_commit_files:
        commit_changes.append(current_commit_files)

    # Calculate Average Entropy
    entropies = [calculate_shannon_entropy(files) for files in commit_changes]
    avg_entropy = sum(entropies) / len(entropies) if entropies else 0.0
    
    print(f"  [Git] Churn: {total_churn}, Authors: {len(authors)}, Avg Entropy: {avg_entropy:.4f}")
    return len(authors), total_churn, avg_entropy

# --- 2. Precision Source Metrics (Lizard Analysis) ---
def scan_source(repo_path):
    print(f"  [Source] Scanning with Lizard (Precision Analysis)...")
    
    # Lizard handles C++, Java, Python etc. perfectly
    # extensions argument is optional, lizard detects automatically, but we can restrict if needed
    extensions = [".c", ".cpp", ".h", ".hpp", ".cc"] 
    files_to_analyze = []
    
    # Find files first
    for root, _, files in os.walk(repo_path):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                files_to_analyze.append(os.path.join(root, file))
    
    # Use lizard to analyze files
    # This parses the AST, much more accurate than regex
    analysis_results = lizard.analyze_files(files_to_analyze, threads=4)
    
    total_nloc = 0
    total_complexity = 0
    file_count = 0
    max_complexity = 0
    
    for file_info in analysis_results:
        file_count += 1
        total_nloc += file_info.nloc
        
        # File complexity is the average complexity of its functions
        if file_info.average_cyclomatic_complexity:
            total_complexity += file_info.average_cyclomatic_complexity
        
        # Check functions for max complexity
        for func in file_info.function_list:
            if func.cyclomatic_complexity > max_complexity:
                max_complexity = func.cyclomatic_complexity

    avg_complexity = total_complexity / file_count if file_count else 0
    
    # Calculate SATD separately (Regex is still best for comments)
    satd_count = 0
    satd_pattern = re.compile(r'\b(FIXME|TODO|HACK|XXX)\b')
    for file_path in files_to_analyze:
        try:
            with open(file_path, 'r', errors='ignore') as f:
                for line in f:
                    if satd_pattern.search(line):
                        satd_count += 1
        except: pass

    # Recalculate MI (Maintainability Index) using accurate NLOC and Complexity
    # Classic formula: 171 - 5.2*ln(aveV) - 0.23*aveG - 16.2*ln(aveLOC)
    # We use a simplified version without Halstead Volume (V) as lizard doesn't output V directly easily
    # MI ~ 171 - 5.2 * log2(NLOC) - 0.23 * Complexity - 16.2 * log2(NLOC)
    # Using base 2 log for approximation
    avg_nloc = total_nloc / file_count if file_count else 1
    mi = 171 - 5.2 * math.log2(avg_nloc) - 0.23 * avg_complexity - 16.2 * math.log2(avg_nloc)
    mi = max(0, min(100, mi)) # Clamp to 0-100

    print(f"  [Source] NLOC: {total_nloc}, Avg CCN: {avg_complexity:.2f}, SATD: {satd_count}")
    return total_nloc, satd_count, avg_complexity, mi

# --- 3. GitHub API Metrics (No changes needed, these are standard) ---
def get_github_metrics(repo, anchor_date):
    print(f"  [GitHub] Fetching metrics...")
    headers = {'Authorization': f'token {TOKEN}', 'Accept': 'application/vnd.github.v3+json'} if TOKEN else {}
    days_back = 1
    since_date = (anchor_date - timedelta(days=days_back)).astimezone(timezone.utc)
    since_str = since_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    search_url = "https://api.github.com/search/issues"

    # Inflow
    inflow = 0
    try:
        r = requests.get(search_url, headers=headers, params={'q': f"repo:{repo} is:issue created:>{since_str}"})
        if r.status_code == 200: inflow = r.json().get('total_count', 0)
    except: pass

    # Outflow
    outflow = 0
    try:
        r = requests.get(search_url, headers=headers, params={'q': f"repo:{repo} is:issue is:closed closed:>{since_str}"})
        if r.status_code == 200: outflow = r.json().get('total_count', 0)
    except: pass

    # Review Window & Rejection
    avg_review = 0
    rejection = 0.0
    try:
        q_closed = f"repo:{repo} is:pr is:closed closed:>{since_str}"
        r_list = requests.get(search_url, headers=headers, params={'q': q_closed})
        if r_list.status_code == 200:
            data = r_list.json()
            total_closed = data.get('total_count', 0)
            if total_closed > 0:
                q_merged = f"repo:{repo} is:pr is:merged merged:>{since_str}"
                r_merged = requests.get(search_url, headers=headers, params={'q': q_merged})
                total_merged = r_merged.json().get('total_count', 0)
                rejection = max(0, total_closed - total_merged) / total_closed
                
                # Calculate timing
                items = data.get('items', [])
                total_time, count = 0, 0
                for item in items:
                    created = datetime.fromisoformat(item['created_at'].replace('Z', '+00:00'))
                    closed = datetime.fromisoformat(item['closed_at'].replace('Z', '+00:00'))
                    total_time += (closed - created).total_seconds()
                    count += 1
                if count: avg_review = (total_time / count) / 3600
    except: pass

    return inflow, outflow, avg_review, rejection

# --- Main Logic ---
def run_collection_task():
    print(f"\n[{datetime.now()}] Starting Hardcore Collection Task...")
    
    if not os.path.exists(REPO_PATH):
        print(f"❌ Error: {REPO_PATH} not found.")
        return

    update_repo(REPO_PATH)
    anchor_date = get_anchor_date(REPO_PATH)
    
    # 1. Precise Source Metrics (Lizard)
    loc, satd, complexity, mi = scan_source(REPO_PATH)
    
    # 2. Advanced Git Metrics (Entropy)
    active_authors, churn, entropy = get_git_metrics(REPO_PATH, anchor_date)
    
    # 3. GitHub Metrics
    inflow, outflow, review_window, rejection = get_github_metrics(GITHUB_REPO, anchor_date)
    
    today_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    file_exists = os.path.isfile(OUTPUT_FILE)
    with open(OUTPUT_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['date', 'inflow', 'outflow', 'satd', 'nloc', 'avg_complexity', 'mi', 'active_authors', 'churn', 'change_entropy', 'review_window', 'rejection_rate'])
        
        writer.writerow([today_str, inflow, outflow, satd, loc, complexity, mi, active_authors, churn, entropy, review_window, rejection])
        
    print(f"✅ Metrics saved. Entropy: {entropy:.4f}, Complexity: {complexity:.2f}")

def start_scheduler():
    print(f"--- Hardcore Metric Collector Started ---")
    while True:
        if TEST_MODE:
            run_collection_task()
            print("Sleeping 60s (Test Mode)...")
            time.sleep(600)
        else:
            now = datetime.now()
            target = now.replace(hour=SCHEDULE_HOUR, minute=0, second=0)
            if now >= target: target += timedelta(days=1)
            wait = (target - now).total_seconds()
            print(f"Next run at {target}")
            time.sleep(wait)
            run_collection_task()

if __name__ == "__main__":
    start_scheduler()