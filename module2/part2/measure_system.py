import os
import re
import json
import csv
import sys
import matplotlib.pyplot as plt

def load_config(config_path='config.json'):
    """Loads the configuration file."""
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found.")
        sys.exit(1)
    with open(config_path, 'r') as f:
        return json.load(f)

def write_to_csv(filepath, data, headers):
    """A helper function to write data to a CSV file."""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    print(f"Successfully wrote data to {filepath}")

def run_analysis(config):
    """
    The main analysis function that scans the repository and generates all data files.
    """
    print("Starting SATD analysis based on configuration...")

    # Extract parameters from config
    repo_path = config['repository_path']
    modules_to_scan = config['modules_to_scan']
    extensions = tuple(config['source_file_extensions'])
    pattern = re.compile(config['satd_patterns'][0])
    thresholds = config['indicator_thresholds']
    output_files = config['output_files']
    
    # Prepare lists to hold the results
    all_base_measures = []
    all_derived_measures = []
    all_indicators = []

    # Prepare the raw data CSV file
    raw_data_file = open(output_files['raw_data'], 'w', newline='', encoding='utf-8')
    raw_data_writer = csv.writer(raw_data_file)
    raw_data_writer.writerow(['module', 'file', 'line_number', 'line_content'])

    # --- Main analysis loop ---
    for module in modules_to_scan:
        module_path = os.path.join(repo_path, module)
        print(f"\nScanning module: {module}...")
        
        if not os.path.isdir(module_path):
            print(f"  [Warning] Directory '{module_path}' not found. Skipping.")
            continue
            
        satd_count = 0
        source_file_count = 0

        for root, _, files in os.walk(module_path):
            for file in files:
                if file.endswith(extensions):
                    source_file_count += 1
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for i, line in enumerate(f, 1):
                                if pattern.search(line):
                                    satd_count += 1
                                    # Write raw data on the fly
                                    raw_data_writer.writerow([module, file_path, i, line.strip()])
                    except Exception:
                        pass # Silently ignore files that cannot be read
        
        print(f"  -> Found {satd_count} SATD comments in {source_file_count} source files.")

        # --- Generate Measures and Indicator for the current module ---
        
        # 1. Base Measure
        base_measure = {'module': module, 'satd_count': satd_count}
        all_base_measures.append(base_measure)
        
        # 2. Derived Measure
        debt_density = (satd_count / source_file_count) if source_file_count > 0 else 0
        derived_measure = {
            'module': module, 
            'debt_density': round(debt_density, 2),
            'source_file_count': source_file_count
        }
        all_derived_measures.append(derived_measure)
        
        # 3. Indicator
        risk_level = 'Low Risk'
        if debt_density >= thresholds['high_risk_density']:
            risk_level = 'High Risk'
        elif debt_density >= thresholds['medium_risk_density']:
            risk_level = 'Medium Risk'
        indicator = {'module': module, 'risk_level': risk_level}
        all_indicators.append(indicator)

    # --- Write all collected data to files ---
    raw_data_file.close()
    print(f"\nSuccessfully wrote raw data to {output_files['raw_data']}")
    
    write_to_csv(output_files['base_measures'], all_base_measures, ['module', 'satd_count'])
    write_to_csv(output_files['derived_measures'], all_derived_measures, ['module', 'debt_density', 'source_file_count'])
    write_to_csv(output_files['indicators'], all_indicators, ['module', 'risk_level'])
    
    print("\nAnalysis complete.")
    return all_base_measures


def visualize_results(base_measures, config):
    """Creates and displays a bar chart from the base measures."""
    if not base_measures:
        print("No metrics to visualize.")
        return
    
    # Sort by count for better visualization
    sorted_measures = sorted(base_measures, key=lambda item: item['satd_count'], reverse=True)
    modules = [item['module'] for item in sorted_measures]
    scores = [item['satd_count'] for item in sorted_measures]

    plt.figure(figsize=(14, 8))
    bars = plt.bar(modules, scores, color='darkcyan')
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval, int(yval), va='bottom', ha='center') 

    plt.xlabel('LLVM Project Module')
    plt.ylabel('Self-Admitted Technical Debt (Count)')
    plt.title('SATD Distribution in LLVM Project Modules')
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    chart_filename = config['output_files']['chart']
    plt.savefig(chart_filename)
    print(f"\nChart saved as {chart_filename}")
    
    plt.show()

# --- Main execution block ---
if __name__ == '__main__':
    config = load_config()

    # Run the full analysis
    final_base_measures = run_analysis(config)
    
    # Visualize the results
    visualize_results(final_base_measures, config)