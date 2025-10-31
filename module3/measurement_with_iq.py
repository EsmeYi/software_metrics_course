# measure_system.py
# This script measures Self-Admitted Technical Debt (SATD) in a given repository,
# calculates derived metrics like debt density, determines risk indicators,
# and incorporates an Information Quality (IQ) system to monitor its own reliability.

import os
import re
import json
import csv
import sys
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta
import subprocess
import pandas as pd # Needed for post-analysis checks

# --- Information Quality (IQ) System Setup ---
# Global list to store the results of all performed IQ checks.
iq_check_results = []

def record_iq_check(check_name, status, details=""):
    """
    Records the result of a single IQ check.
    Args:
        check_name (str): A descriptive name for the check.
        status (str): The outcome ('PASS', 'WARN', 'FAIL').
        details (str, optional): Additional information about the result.
    """
    iq_check_results.append({
        "timestamp": datetime.now().isoformat(),
        "check_name": check_name,
        "status": status,
        "details": details
    })
    # Provide immediate feedback in the console for non-passing checks.
    if status != 'PASS':
        print(f"  [IQ {status}] {check_name}: {details}")

# --- Helper function to collect extensions (needed by load_config) ---
def get_repo_extensions(repo_path, max_depth=3, sample_limit=5000):
    """
    Scans the repository up to a certain depth or file limit
    to find common file extensions. Returns a set of unique extensions found.
    """
    found_extensions = set()
    file_count = 0
    if not repo_path or not os.path.isdir(repo_path):
        print(f"  [Warning] Cannot scan for extensions: Repository path '{repo_path}' is invalid.")
        return None

    try:
        print("\nScanning repository for file extensions (this might take a moment)...")
        for root, dirs, files in os.walk(repo_path):
            depth = root[len(repo_path):].count(os.sep)
            if depth >= max_depth:
                dirs[:] = [] # Don't go deeper

            for file in files:
                file_count += 1
                if '.' in file:
                    ext = os.path.splitext(file)[1].lower()
                    if ext:
                        found_extensions.add(ext)
                if file_count >= sample_limit:
                    print(f"  [Info] Reached file sample limit ({sample_limit}) for extension check.")
                    return found_extensions
        print(f"  [Info] Scanned {file_count} files for extensions.")
        return found_extensions
    except Exception as e:
        print(f"  [Warning] Could not complete repository extension scan: {e}")
        return None

# --- Configuration Loading with IQ Checks ---
def load_config(config_path='config.json'):
    """
    Loads the configuration file and performs initial IQ checks on its validity
    and the completeness of its parameters.
    """
    config = None
    # Consolidated Check: Config File Health
    check_name = "Config File Health (Exists, Readable, Valid JSON)"
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        record_iq_check(check_name, "PASS", f"Successfully loaded and parsed {config_path}")
    except FileNotFoundError:
        details = f"File not found: {config_path}"
        record_iq_check(check_name, "FAIL", details)
        print(f"Critical Error: {details}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        details = f"Invalid JSON format in {config_path}: {e}"
        record_iq_check(check_name, "FAIL", details)
        print(f"Critical Error: {details}")
        sys.exit(1)
    except Exception as e:
        details = f"Cannot read or process {config_path}: {e}"
        record_iq_check(check_name, "FAIL", details)
        print(f"Critical Error: {details}")
        sys.exit(1)

    # --- Configuration Content IQ Checks ---
    repo_path_valid = False
    repo_path = config.get('repository_path')
    if repo_path and os.path.isdir(repo_path):
        record_iq_check("Repo Path Exists & Is Directory", "PASS", repo_path)
        repo_path_valid = True
    else:
        record_iq_check("Repo Path Exists & Is Directory", "FAIL", f"Path not found or not a directory: {repo_path}")

    modules = config.get('modules_to_scan')
    if isinstance(modules, list) and modules:
        record_iq_check("Modules List Valid (Format)", "PASS", f"{len(modules)} modules specified")
    else:
        record_iq_check("Modules List Valid (Format)", "FAIL", "'modules_to_scan' is not a non-empty list")

    extensions = config.get('source_file_extensions')
    configured_extensions = set()
    if isinstance(extensions, list) and extensions:
        record_iq_check("Extensions List Valid (Format)", "PASS", f"{len(extensions)} extensions specified")
        configured_extensions = set(extensions)
    else:
        record_iq_check("Extensions List Valid (Format)", "FAIL", "'source_file_extensions' is not a non-empty list")

    # Extensions Completeness Check
    if repo_path_valid and configured_extensions:
        found_exts = get_repo_extensions(repo_path)
        if found_exts is not None:
            potentially_relevant = {'.td', '.py', '.cmake', '.test', '.lit', '.ll', '.mir'}
            missing_relevant = (potentially_relevant.intersection(found_exts)) - configured_extensions
            if missing_relevant:
                record_iq_check("Extensions List Completeness", "WARN",
                                f"Potentially relevant extensions in repo but not in config: {sorted(list(missing_relevant))}")
            else:
                 record_iq_check("Extensions List Completeness", "PASS",
                                 "Configured extensions cover common/expected types.")
        else:
             record_iq_check("Extensions List Completeness", "FAIL",
                             "Could not scan repository for extensions.")
    elif not repo_path_valid:
         record_iq_check("Extensions List Completeness", "FAIL", "Skipped: repository path is invalid.")

    patterns = config.get('satd_patterns')
    if isinstance(patterns, list) and patterns:
        try:
            re.compile(patterns[0])
            record_iq_check("SATD Pattern Valid (Regex)", "PASS", patterns[0])
        except re.error as e:
            record_iq_check("SATD Pattern Valid (Regex)", "FAIL", f"Invalid regex '{patterns[0]}': {e}")
    else:
        record_iq_check("SATD Pattern Valid (Regex)", "FAIL", "'satd_patterns' is not a non-empty list.")

    thresholds = config.get('indicator_thresholds')
    if isinstance(thresholds, dict) and 'high_risk_density' in thresholds and 'medium_risk_density' in thresholds:
        record_iq_check("Thresholds Valid (Format)", "PASS")
    else:
        record_iq_check("Thresholds Valid (Format)", "FAIL", "'indicator_thresholds' format is incorrect.")

    outputs = config.get('output_files')
    required_outputs = ['raw_data', 'base_measures', 'derived_measures', 'indicators', 'chart']
    if isinstance(outputs, dict) and all(key in outputs for key in required_outputs):
        record_iq_check("Output Files Config Valid (Keys)", "PASS")
    else:
        record_iq_check("Output Files Config Valid (Keys)", "FAIL", f"'output_files' missing required keys.")

    print("-" * 30)
    return config

# --- Simplified CSV Writing Helper ---
def write_to_csv(filepath, data, headers):
    """Writes data to a CSV file."""
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
        print(f"Successfully wrote data to {filepath}")
    except Exception as e:
        print(f"  [Error] Failed to write to {filepath}: {e}")

# --- Git Repository Status Checks ---
def check_git_status(repo_path):
    """Performs Git status checks and records IQ results."""
    try:
        subprocess.run(['git', '-C', repo_path, 'rev-parse', '--is-inside-work-tree'],
                       check=True, capture_output=True, text=True, errors='ignore')
        record_iq_check("Git: Is Git Repository", "PASS", repo_path)
    except (subprocess.CalledProcessError, FileNotFoundError):
        record_iq_check("Git: Is Git Repository", "FAIL", f"{repo_path} is not a valid Git repo.")
        return False # Indicate failure

    # Check 1: Current Branch
    try:
        result_branch = subprocess.run(['git', '-C', repo_path, 'rev-parse', '--abbrev-ref', 'HEAD'],
                                       check=True, capture_output=True, text=True, errors='ignore')
        current_branch = result_branch.stdout.strip()
        expected_branch = 'main'
        if current_branch == expected_branch:
            record_iq_check("Git: On Expected Branch", "PASS", f"Current branch is '{current_branch}'")
        else:
            record_iq_check("Git: On Expected Branch", "WARN", f"Expected '{expected_branch}', but is '{current_branch}'")
    except subprocess.CalledProcessError as e:
        record_iq_check("Git: Check Branch Failed", "FAIL", f"Could not determine branch: {e}")

    # Check 2: Last Commit Date
    try:
        result_date = subprocess.run(['git', '-C', repo_path, 'log', '-1', '--format=%cd', '--date=iso-strict'],
                                     check=True, capture_output=True, text=True, errors='ignore')
        last_commit_iso_str = result_date.stdout.strip()
        last_commit_dt = datetime.fromisoformat(last_commit_iso_str)
        today = datetime.now().astimezone().date()
        commit_date = last_commit_dt.astimezone().date()
        if commit_date == today:
            record_iq_check("Git: Latest Commit is Today", "PASS", f"Last commit: {commit_date}")
        else:
            days_diff = (today - commit_date).days
            record_iq_check("Git: Latest Commit is Today", "WARN", f"Last commit was {days_diff} days ago ({commit_date}).")
    except (ValueError, subprocess.CalledProcessError) as e:
        record_iq_check("Git: Check Commit Date Failed", "FAIL", f"Could not get or parse last commit date: {e}")

    # Check 3: Shallow Clone
    try:
        result = subprocess.run(['git', '-C', repo_path, 'rev-parse', '--is-shallow-repository'],
                                 check=True, capture_output=True, text=True, errors='ignore')
        if result.stdout.strip() == 'true':
            record_iq_check("Git History Depth", "WARN", "Repository is a shallow clone, historical data is incomplete.")
        else:
            record_iq_check("Git History Depth", "PASS", "Repository is a full clone.")
    except Exception as e:
        record_iq_check("Git History Depth", "WARN", f"Could not check if repository is shallow: {e}")

    return True # Indicate Git checks were performed

# --- Helper for Alternative Pattern Check ---
def check_alternative_satd_patterns(repo_path, modules_to_scan, extensions, patterns_to_check, limit_per_pattern=5):
    """
    Performs a limited scan for alternative SATD patterns not caught by the main regex.
    """
    findings = {name: [] for name in patterns_to_check}
    compiled_patterns = {name: re.compile(pattern) for name, pattern in patterns_to_check.items()}
    files_scanned = 0
    MAX_SCAN_FILES = 1000

    print(f"\nPerforming limited scan for alternative SATD patterns...")
    try:
        for module in modules_to_scan:
            module_path = os.path.join(repo_path, module)
            if not os.path.isdir(module_path): continue
            for root, _, files in os.walk(module_path):
                 if files_scanned >= MAX_SCAN_FILES: break
                 for file in files:
                     if files_scanned >= MAX_SCAN_FILES: break
                     if file.endswith(extensions):
                         files_scanned += 1
                         file_path = os.path.join(root, file)
                         try:
                             with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                 for i, line in enumerate(f, 1):
                                     for name, pattern in compiled_patterns.items():
                                         # Stop searching for a pattern once limit is reached
                                         if len(findings[name]) < limit_per_pattern and pattern.search(line):
                                             findings[name].append(f"{os.path.basename(file_path)}:{i}") # Shorter path
                         except Exception: pass
            if files_scanned >= MAX_SCAN_FILES: break
        print(f"  Limited scan checked {files_scanned} files.")

        for name, found_locations in findings.items():
            if found_locations:
                record_iq_check(f"Found '{name}'", "WARN",
                                f"Found examples missed by main pattern (limit {limit_per_pattern}): {found_locations}")
            else:
                 record_iq_check(f"Found '{name}'", "PASS",
                                 f"Limited scan found no obvious examples.")
    except Exception as e:
        record_iq_check("Alternative Pattern Scan", "FAIL", f"Scan failed: {e}")

# --- Consolidated Output File Check Function ---
def check_output_files_status(config):
    """Performs a single, consolidated IQ check on all expected output files."""
    output_files = config.get('output_files', {})
    if not output_files:
        record_iq_check("All Output Files Generated", "FAIL", "Output files not defined in config.")
        return
    missing_files, empty_files = [], []
    for key, filepath in output_files.items():
        if not os.path.exists(filepath):
            missing_files.append(os.path.basename(filepath))
        elif os.path.exists(filepath) and key != 'chart': # Don't check size for chart image
            try:
                if os.path.getsize(filepath) <= 1: # Check if only header exists or empty
                    empty_files.append(os.path.basename(filepath))
            except OSError:
                 empty_files.append(f"{os.path.basename(filepath)} (unreadable?)")
    details = []
    if missing_files: details.append(f"Missing files: {missing_files}")
    if empty_files: details.append(f"Empty/Unreadable files: {empty_files}")
    if not details:
        record_iq_check("All Output Files Generated", "PASS", f"All {len(output_files)} files created and populated.")
    else:
        record_iq_check("All Output Files Generated", "WARN", "; ".join(details))

# --- Main Analysis Function ---
def run_analysis(config):
    """Scans the repository for SATD and generates measures and indicators."""
    print("\nStarting SATD analysis based on configuration...")
    repo_path = config['repository_path']
    modules_to_scan = config.get('modules_to_scan', [])
    extensions = tuple(config.get('source_file_extensions', []))
    try:
        main_pattern_str = config.get('satd_patterns', ["^$"])[0]
        pattern = re.compile(main_pattern_str)
    except re.error:
        pattern = re.compile("^$")
    thresholds = config.get('indicator_thresholds', {})
    output_files = config.get('output_files', {})

    if repo_path and os.path.isdir(repo_path):
        git_ok = check_git_status(repo_path)
        # Perform alternative pattern check if git repo is valid (or skip?)
        alternative_patterns = {
            "Lowercase Tags (with colon)": r'\b(fixme|todo|hack|xxx):',
            "Uppercase Tags (no colon)": r'\b(FIXME|TODO|HACK|XXX)\b'
        }
        if extensions: # Only check if extensions are configured
            check_alternative_satd_patterns(repo_path, modules_to_scan, extensions, alternative_patterns)
    else:
         print("Warning: Skipping Git checks and alternative pattern scan due to invalid repo path.")


    all_base_measures, all_derived_measures, all_indicators = [], [], []
    read_error_count, all_modules_found, missing_modules_list = 0, True, []
    modules_with_satd = set()
    successfully_scanned_modules = set()

    # IQ Check: Module List Completeness (repo vs config)
    try:
        if repo_path and os.path.isdir(repo_path):
            actual_dirs = [d for d in os.listdir(repo_path) if os.path.isdir(os.path.join(repo_path, d))]
            missing_in_config = [d for d in actual_dirs if d not in modules_to_scan and not d.startswith('.')]
            if missing_in_config: record_iq_check("Module List Config", "WARN", f"Modules in repo not in config: {missing_in_config}")
            else: record_iq_check("Module List Config", "PASS")
        else:
             record_iq_check("Module List Config", "FAIL", "Cannot perform check: Invalid repo path.")
    except Exception as e: record_iq_check("Module List Config", "WARN", f"Check failed: {e}")

    raw_data_filepath = output_files.get('raw_data', 'raw_satd_data.csv')
    raw_data_file = None
    try:
        raw_data_file = open(raw_data_filepath, 'w', newline='', encoding='utf-8')
        raw_data_writer = csv.writer(raw_data_file)
        raw_data_writer.writerow(['module', 'file', 'line_number', 'line_content'])
        record_iq_check("File Access: Raw Data File Openable", "PASS", raw_data_filepath)
    except Exception as e:
        record_iq_check("File Access: Raw Data File Openable", "FAIL", f"Cannot open {raw_data_filepath}: {e}")

    for module in modules_to_scan:
        module_path = os.path.join(repo_path, module)
        print(f"\nScanning module: {module}...")
        if not os.path.isdir(module_path):
            all_modules_found = False
            missing_modules_list.append(module)
            print(f"  [Warning] Directory not found. Skipping.")
            continue
        
        successfully_scanned_modules.add(module)
        satd_count, source_file_count, module_read_errors = 0, 0, 0
        
        for root, _, files in os.walk(module_path):
            for file in files:
                if file.endswith(extensions):
                    source_file_count += 1
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                            for i, line in enumerate(f, 1):
                                if pattern.search(line):
                                    satd_count += 1
                                    if raw_data_file:
                                        raw_data_writer.writerow([module, os.path.join(root, file), i, line.strip()])
                    except Exception:
                        module_read_errors += 1
        
        read_error_count += module_read_errors
        if module_read_errors > 0:
            record_iq_check("File Readability Impact", "WARN", f"{module_read_errors} read errors in '{module}'")

        print(f"  -> Found {satd_count} SATD comments in {source_file_count} source files.")
        
        if source_file_count == 0:
            record_iq_check("Zero Relevant Files", "WARN", f"Module '{module}' has 0 files matching extensions.")

        if satd_count > 0:
            modules_with_satd.add(module)

        all_base_measures.append({'module': module, 'satd_count': satd_count})
        debt_density = (satd_count / source_file_count) if source_file_count > 0 else 0
        all_derived_measures.append({'module': module, 'debt_density': round(debt_density, 2), 'source_file_count': source_file_count})
        risk_level = 'Low Risk'
        high_thresh = thresholds.get('high_risk_density', 2.0)
        med_thresh = thresholds.get('medium_risk_density', 1.0)
        if debt_density >= high_thresh: risk_level = 'High Risk'
        elif debt_density >= med_thresh: risk_level = 'Medium Risk'
        all_indicators.append({'module': module, 'risk_level': risk_level})

    if all_modules_found: record_iq_check("All Configured Modules Exist", "PASS")
    else: record_iq_check("All Configured Modules Exist", "WARN", f"Missing modules from config: {missing_modules_list}")

    if read_error_count > 0: record_iq_check("Overall File Readability Impact", "WARN", f"Total {read_error_count} file read errors")
    else: record_iq_check("Overall File Readability Impact", "PASS")

    if raw_data_file: raw_data_file.close()

    base_measure_file = output_files.get('base_measures', 'base_measures.csv')
    derived_measure_file = output_files.get('derived_measures', 'derived_measures.csv')
    indicators_file = output_files.get('indicators', 'indicators.csv')
    
    write_to_csv(base_measure_file, all_base_measures, ['module', 'satd_count'])
    write_to_csv(derived_measure_file, all_derived_measures, ['module', 'debt_density', 'source_file_count'])
    write_to_csv(indicators_file, all_indicators, ['module', 'risk_level'])

    print("\nAnalysis complete.")

    # --- Post-Analysis IQ Checks for Completeness ---
    try:
        if os.path.exists(raw_data_filepath) and os.path.getsize(raw_data_filepath) > 10: # Check size > header
            df_raw = pd.read_csv(raw_data_filepath)
            modules_in_raw = set(df_raw['module'].unique())
            if modules_in_raw == modules_with_satd: record_iq_check("Raw Data Logging", "PASS")
            else: record_iq_check("Raw Data Logging", "WARN", f"Module mismatch raw vs found SATD.")
        elif modules_with_satd: record_iq_check("Raw Data Logging", "FAIL", "SATD found but raw file empty/missing.")
        else: record_iq_check("Raw Data Logging", "PASS", "No SATD found, raw file empty.")
    except Exception as e: record_iq_check("Raw Data Logging", "FAIL", f"Check failed: {e}")
    try:
        if os.path.exists(base_measure_file):
            df_base = pd.read_csv(base_measure_file)
            if set(df_base['module'].unique()) == successfully_scanned_modules: record_iq_check("Base Measures Output", "PASS")
            else: record_iq_check("Base Measures Output", "WARN", "Module mismatch base vs scanned.")
        else: record_iq_check("Base Measures Output", "FAIL", "File not created.")
    except Exception as e: record_iq_check("Base Measures Output", "FAIL", f"Check failed: {e}")
    try:
        if os.path.exists(derived_measure_file):
            df_derived = pd.read_csv(derived_measure_file)
            if set(df_derived['module'].unique()) == successfully_scanned_modules: record_iq_check("Derived Measures Output", "PASS")
            else: record_iq_check("Derived Measures Output", "WARN", "Module mismatch derived vs scanned.")
        else: record_iq_check("Derived Measures Output", "FAIL", "File not created.")
    except Exception as e: record_iq_check("Derived Measures Output", "FAIL", f"Check failed: {e}")
    try:
        if os.path.exists(indicators_file):
            df_indicators = pd.read_csv(indicators_file)
            if set(df_indicators['module'].unique()) == successfully_scanned_modules: record_iq_check("Indicators Output", "PASS")
            else: record_iq_check("Indicators Output", "WARN", "Module mismatch indicators vs scanned.")
        else: record_iq_check("Indicators Output", "FAIL", "File not created.")
    except Exception as e: record_iq_check("Indicators Output", "FAIL", f"Check failed: {e}")

    return all_base_measures

# --- Define IQ Attribute Categories for Checks ---
IQ_ATTRIBUTE_MAP = {
    # Free-of-Error (Objective correctness, format, accessibility, execution)
    "Config File Health": "Free-of-Error",
    "Repo Path Exists & Is Directory": "Free-of-Error",
    "Modules List Valid (Format)": "Free-of-Error",
    "Extensions List Valid (Format)": "Free-of-Error",
    "SATD Pattern Valid (Regex)": "Free-of-Error",
    "Thresholds Valid (Format)": "Free-of-Error",
    "Output Files Config Valid (Keys)": "Free-of-Error",
    "File Access: Raw Data File Openable": "Free-of-Error",
    "Git: Is Git Repository": "Free-of-Error",
    "Git: Check Branch Failed": "Free-of-Error",
    "Git: Check Commit Date Failed": "Free-of-Error",
    "Git: Parse Commit Date Failed": "Free-of-Error",
    "Git: On Expected Branch": "Free-of-Error", # More about Scope/Relevance
    "Git: Latest Commit is Today": "Free-of-Error", # More about Timeliness

    # Completeness (Coverage, missing data, undercounting)
    "Extensions List Completeness": "Completeness",
    "Module List Completeness": "Completeness", # Repo vs Config
    "All Configured Modules Exist": "Completeness", # Config vs Repo
    "Found 'Lowercase Tags": "Completeness",
    "Found 'Uppercase Tags": "Completeness",
    "Git History Depth": "Completeness",
    "File Readability Impact": "Completeness",
    "Zero Relevant Files": "Completeness",
    "Raw Data Logging": "Completeness",
    "Base Measures Output": "Completeness",
    "Derived Measures Output": "Completeness",
    "Indicators Output": "Completeness",
    "All Output Files Generated": "Completeness", # Covers existence and non-emptiness
    "Alternative Pattern Scan": "Completeness" # Meta-check for scan process
}


# --- IQ Visualization Function (Grouped by Attribute) ---
def visualize_iq_results(iq_results):
    """Creates grouped bar charts visualizing the status of IQ checks by attribute."""
    if not iq_results:
        print("No IQ check results to visualize.")
        return

    final_checks = {}
    for check in iq_results:
        name = check['check_name']
        current_status = check['status']
        priority = {'FAIL': 3, 'WARN': 2, 'PASS': 1}
        # Only update if the new status is 'worse' or check doesn't exist yet
        if name not in final_checks or priority[current_status] > priority[final_checks[name]['status']]:
            final_checks[name] = check

    categorized_checks = {"Free-of-Error": [], "Completeness": [], "Other": []}
    for name, result in final_checks.items():
        attribute = "Other" # Default
        # Find attribute, using startswith for flexibility (e.g., "Completeness:")
        for map_key, attr_value in IQ_ATTRIBUTE_MAP.items():
            if name == map_key or name.startswith(map_key):
                 attribute = attr_value
                 break
        categorized_checks[attribute].append(result)

    attributes_to_plot = ["Free-of-Error", "Completeness"]
    num_attributes = len(attributes_to_plot)
    total_checks_count = len(final_checks)
    fig_height = max(6, total_checks_count * 0.4 + num_attributes * 1.5)
    fig, axes = plt.subplots(num_attributes, 1, figsize=(10, fig_height), sharex=True)
    if num_attributes == 1: axes = [axes]

    fig.suptitle('Information Quality Check Results by Attribute', fontsize=16, y=0.99)
    status_map = {'PASS': 1, 'WARN': 0.5, 'FAIL': 0}
    color_map = {'PASS': 'green', 'WARN': 'red', 'FAIL': 'firebrick'}
    overall_pass_count, overall_total_checks = 0, 0

    for i, attribute in enumerate(attributes_to_plot):
        ax = axes[i]
        checks_in_category = sorted(categorized_checks[attribute], key=lambda x: x['check_name'])

        if not checks_in_category:
            ax.text(0.5, 0.5, 'No checks in this category', ha='center', va='center')
            ax.set_title(f'{attribute} (0 Checks)')
            ax.set_yticks([])
            continue

        check_names = [r['check_name'] for r in checks_in_category]
        statuses = [r['status'] for r in checks_in_category]
        numeric_statuses = [status_map.get(s, 0) for s in statuses]
        colors = [color_map.get(s, 'grey') for s in statuses]
        pass_count = statuses.count('PASS')
        total_category_checks = len(statuses)
        pass_rate = (pass_count / total_category_checks) * 100 if total_category_checks > 0 else 0
        overall_pass_count += pass_count
        overall_total_checks += total_category_checks
        y_pos = range(total_category_checks)
        bars = ax.barh(y_pos, numeric_statuses, color=colors, tick_label=check_names)
        for j, bar in enumerate(bars):
            ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height()/2, statuses[j], va='center', ha='left', fontsize=11)
        ax.set_title(f'{attribute} ({pass_rate:.1f}% Passed)')
        ax.set_yticks(y_pos); ax.set_yticklabels(check_names, fontsize=11); ax.invert_yaxis()

    axes[-1].set_xlabel('Status')
    axes[-1].set_xticks([0, 0.5, 1]); axes[-1].set_xticklabels(['FAIL', 'WARN', 'PASS'])
    plt.xlim(right=1.3) # More space for labels
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])

    iq_chart_filename = 'iq_check_results_by_attribute.pdf'
    plt.savefig(iq_chart_filename)
    print(f"\nIQ results chart saved as {iq_chart_filename}")
    plt.show()

# --- SATD Results Visualization Function ---
def visualize_results(base_measures, config):
    """Creates and displays the main SATD distribution bar chart."""
    if not base_measures: return
    sorted_measures = sorted(base_measures, key=lambda item: item['satd_count'], reverse=True)
    modules = [item['module'] for item in sorted_measures]
    scores = [item['satd_count'] for item in sorted_measures]
    plt.figure(figsize=(14, 8))
    bars = plt.bar(modules, scores, color='teal')
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval, int(yval), va='bottom', ha='center', fontsize=10)
    plt.xlabel(' '); plt.ylabel(' ')
    plt.title('SATD Distribution in LLVM Project Modules')
    plt.xticks(rotation=45, ha='right', fontsize=12); plt.yticks(fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7); plt.tight_layout()
    chart_filename = 'satd_distribution_chart.pdf'
    plt.savefig(chart_filename)
    print(f"\nSATD results chart saved as {chart_filename}")
    plt.show()

# --- Main Execution Block ---
if __name__ == '__main__':
    # 1. Load config and perform initial IQ checks
    config = load_config()
    if not config: sys.exit(1)
    # 2. Run the analysis, which includes embedded IQ checks
    final_base_measures = run_analysis(config)
    # 3. Visualize the main SATD results (this saves the SATD chart file)
    visualize_results(final_base_measures, config)
    # 4. NOW perform the consolidated output check
    check_output_files_status(config)
    # 5. Visualize the COMPLETE IQ check results, grouped by attribute
    visualize_iq_results(iq_check_results)
    # 6. Save the IQ log for auditing/review
    try:
        with open('iq_check_log.json', 'w') as f:
            json.dump(iq_check_results, f, indent=2, ensure_ascii=False)
        print("\nIQ check log saved to iq_check_log.json")
    except Exception as e:
        print(f"\nWarning: Could not save IQ check log: {e}")
