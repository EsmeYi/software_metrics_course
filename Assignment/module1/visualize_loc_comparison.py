# scripts/visualize_loc_comparison.py

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

def get_module_from_path(path, repo_name, depth=1):
    """
    Extracts the module name from a file path up to a specified depth,
    after stripping the repository name prefix.
    """
    clean_path = str(path)
    # Remove leading ./ if it exists
    if clean_path.startswith('./'):
        clean_path = clean_path[2:]
    
    # Remove repository name prefix if it exists
    prefix = repo_name + os.sep
    if clean_path.startswith(prefix):
        clean_path = clean_path[len(prefix):]

    parts = clean_path.split(os.sep)
    
    if len(parts) <= depth:
        module_parts = parts[:-1]
        if module_parts:
            return os.sep.join(module_parts)
        else:
            return '(Root)'
            
    return os.sep.join(parts[:depth])

def load_ploc_data(filepath, repo_name):
    """Loads physical LOC data from cloc's report."""
    try:
        df = pd.read_csv(filepath)
        if 'SUM' in df['language'].values:
            df = df[df['language'] != 'SUM'].copy()
        df['module'] = df['filename'].apply(lambda p: get_module_from_path(p, repo_name, depth=1))
        ploc_by_module = df.groupby('module')['code'].sum().reset_index()
        ploc_by_module.rename(columns={'code': 'pLOC'}, inplace=True)
        return ploc_by_module
    except Exception as e:
        sys.exit(f"Error reading or processing pLOC file '{filepath}': {e}")

def load_lloc_data(filepath, repo_name):
    """Loads logical LOC data from lizard's report."""
    try:
        col_names = ['NLOC', 'CCN', 'Token', 'Parameters', 'Length', 'Location', 
                     'FilePath', 'FunctionName', 'FullSignature', 'StartLine', 'EndLine']
        df = pd.read_csv(filepath, header=None, names=col_names)
        df['module'] = df['FilePath'].apply(lambda p: get_module_from_path(p, repo_name, depth=1))
        lloc_by_module = df.groupby('module')['NLOC'].sum().reset_index()
        lloc_by_module.rename(columns={'NLOC': 'lLOC'}, inplace=True)
        return lloc_by_module
    except Exception as e:
        sys.exit(f"Error reading or processing lLOC file '{filepath}': {e}")

def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python visualize_loc_comparison.py <path_to_loc_report.csv> <path_to_complexity_report.csv>")

    ploc_csv_path = sys.argv[1]
    lloc_csv_path = sys.argv[2]

    for path in [ploc_csv_path, lloc_csv_path]:
        if not os.path.exists(path):
            sys.exit(f"Error: File not found at '{path}'")
            
    # Automatically detect repository name from the path
    repo_name = os.path.basename(os.path.dirname(ploc_csv_path))
    print(f"Detected repository name: '{repo_name}'")

    print("Loading and processing LOC data...")
    ploc_data = load_ploc_data(ploc_csv_path, repo_name)
    lloc_data = load_lloc_data(lloc_csv_path, repo_name)

    print("Merging pLOC and lLOC data...")
    merged_df = pd.merge(ploc_data, lloc_data, on='module', how='outer').fillna(0)
    
    # Exclude (Root) module for a cleaner plot of source code modules
    merged_df = merged_df[merged_df['module'] != '(Root)']

    # Sort by pLOC to show the largest modules
    merged_df.sort_values(by='pLOC', ascending=False, inplace=True)
    
    top_n = 20
    plot_df = merged_df.head(top_n)

    print(f"Generating comparison plot for the top {top_n} modules...")
    
    # --- Plotting ---
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(14, 10))
    
    positions = range(len(plot_df))
    width = 0.4
    
    ax.barh([p - width/2 for p in positions], plot_df['pLOC'], height=width, label='Physical LOC (pLOC)', color='skyblue')
    ax.barh([p + width/2 for p in positions], plot_df['lLOC'], height=width, label='Logical LOC (lLOC)', color='salmon')

    ax.set_yticks(positions)
    ax.set_yticklabels(plot_df['module'])
    ax.invert_yaxis()
    ax.set_xlabel('Lines of Code', fontsize=12)
    ax.set_ylabel('Module (Top-Level Directory)', fontsize=12)
    ax.set_title(f'Comparison of Physical vs. Logical LOC for Top {top_n} Modules', fontsize=16)
    ax.legend()
    
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    plt.xticks(rotation=45)
    
    fig.tight_layout()
    
    # --- Saving the plot ---
    output_dir = os.path.join(os.path.dirname(ploc_csv_path), 'plots')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_filename = os.path.join(output_dir, '5_ploc_vs_lloc_comparison.png')
    
    fig.savefig(output_filename, dpi=300)
    print(f"\nComparison plot saved to: {output_filename}")

if __name__ == '__main__':
    main()