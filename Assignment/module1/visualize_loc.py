# scripts/visualize_loc.py

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as mticker

# --- Helper Functions ---

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
    
    # If the path has fewer parts than the depth, or it's a file in the module root
    if len(parts) <= depth:
         # Take all parts except the last one (filename)
        module_parts = parts[:-1]
        if module_parts:
            return os.sep.join(module_parts)
        else:
            # This is a file directly inside the repo root after cleaning
            return '(Root)'
            
    return os.sep.join(parts[:depth])


def save_plot(fig, output_path, filename):
    """Saves a matplotlib figure to a specified path."""
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    full_path = os.path.join(output_path, filename)
    fig.savefig(full_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {full_path}")
    plt.close(fig)

# --- Plotting Functions ---

def plot_loc_by_language(df, output_path):
    """Visualizes lines of code aggregated by programming language."""
    lang_loc = df.groupby('language')['code'].sum().sort_values(ascending=False)
    
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(12, 8))
    
    sns.barplot(x=lang_loc.values, y=lang_loc.index, ax=ax, palette='viridis')
    
    ax.set_title('Total Lines of Code by Programming Language', fontsize=16)
    ax.set_xlabel('Lines of Code (LOC)', fontsize=12)
    ax.set_ylabel('Language', fontsize=12)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    
    for i, v in enumerate(lang_loc.values):
        ax.text(v + (lang_loc.values.max() * 0.01), i, f'{v:,}', color='black', va='center')
        
    save_plot(fig, output_path, '1_loc_by_language.png')

def plot_loc_by_module(df, output_path, repo_name, top_n=20, depth=1):
    """
    Visualizes lines of code by module, with adjustable directory depth.
    """
    print(f"Aggregating modules for repo '{repo_name}' at depth={depth}...")
    df['module'] = df['filename'].apply(
        lambda p: get_module_from_path(p, repo_name, depth=depth)
    )
    
    # Exclude root files for a cleaner module chart
    df_filtered = df[df['module'] != '(Root)']
    
    module_loc = df_filtered.groupby('module')['code'].sum().sort_values(ascending=False).head(top_n)
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    sns.barplot(x=module_loc.values, y=module_loc.index, ax=ax, palette='plasma')
    
    ax.set_title(f'Top {top_n} Largest Modules (Depth={depth}) by LOC', fontsize=16)
    ax.set_xlabel('Lines of Code (LOC)', fontsize=12)
    ax.set_ylabel(f'Module (Depth={depth})', fontsize=12)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: format(int(x), ',')))

    for i, v in enumerate(module_loc.values):
        ax.text(v + (module_loc.values.max() * 0.01), i, f'{v:,}', color='black', va='center')
        
    save_plot(fig, output_path, f'2_loc_by_module_depth_{depth}.png')

def plot_file_size_distribution(df, output_path):
    """Visualizes the distribution of file sizes as a histogram."""
    reasonable_loc = df[df['code'] <= df['code'].quantile(0.99)]['code']
    
    fig, ax = plt.subplots(figsize=(12, 7))
    sns.histplot(reasonable_loc, bins=50, kde=True, ax=ax)
    ax.set_title('Distribution of File Sizes (up to 99th Percentile)', fontsize=16)
    ax.set_xlabel('Lines of Code (LOC) per File', fontsize=12)
    ax.set_ylabel('Number of Files', fontsize=12)
    
    save_plot(fig, output_path, '3_file_size_distribution.png')

def plot_top_n_largest_files(df, output_path, top_n=20):
    """Visualizes the top N largest files by lines of code."""
    top_files = df.nlargest(top_n, 'code')
    
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.barplot(x=top_files['code'], y=top_files['filename'], ax=ax, palette='magma')
    ax.set_title(f'Top {top_n} Largest Files by Lines of Code', fontsize=16)
    ax.set_xlabel('Lines of Code (LOC)', fontsize=12)
    ax.set_ylabel('File Name', fontsize=12)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    
    save_plot(fig, output_path, '4_top_largest_files.png')

# --- Main Execution Logic ---

def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python visualize_loc.py <path_to_loc_report.csv>")
        
    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        sys.exit(f"Error: File not found at '{csv_path}'")
        
    results_dir = os.path.dirname(csv_path)
    output_plot_dir = os.path.join(results_dir, 'plots')
    
    # --- NEW: Automatically detect repository name ---
    repo_name = os.path.basename(results_dir)
    print(f"Detected repository name: '{repo_name}'")
    
    print(f"Loading data from: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
        if 'SUM' in df['language'].values:
            df = df[df['language'] != 'SUM'].copy()
    except Exception as e:
        sys.exit(f"Error reading CSV file: {e}")

    print("Generating plots...")
    
    plot_loc_by_language(df, output_plot_dir)
    # Pass the detected repo_name to the plotting function
    plot_loc_by_module(df, output_plot_dir, repo_name, top_n=20, depth=1) 
    plot_loc_by_module(df, output_plot_dir, repo_name, top_n=20, depth=2)
    plot_file_size_distribution(df, output_plot_dir)
    plot_top_n_largest_files(df, output_plot_dir)
    
    print("\nAll plots generated successfully!")

if __name__ == '__main__':
    main()