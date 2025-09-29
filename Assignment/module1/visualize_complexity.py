# scripts/visualize_complexity.py

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as mticker

# --- Helper Functions ---

def save_plot(fig, output_path, filename):
    """Saves a matplotlib figure to a specified path."""
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    full_path = os.path.join(output_path, filename)
    fig.savefig(full_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {full_path}")
    plt.close(fig)

def load_complexity_data(filepath):
    """Loads and cleans the complexity data from lizard's report."""
    try:
        # Lizard's CSV has no header, so we provide column names
        col_names = ['NLOC', 'CCN', 'Token', 'Parameters', 'Length', 'Location', 
                     'FilePath', 'FunctionName', 'FullSignature', 'StartLine', 'EndLine']
        df = pd.read_csv(filepath, header=None, names=col_names)
        # Clean up function name for better plotting
        df['DisplayName'] = df['FunctionName'] + '@' + df['FilePath']
        return df
    except Exception as e:
        sys.exit(f"Error reading or processing complexity file '{filepath}': {e}")

# --- Plotting Functions ---

def plot_complexity_distribution(df, output_path):
    """Visualizes the distribution of Cyclomatic Complexity (CCN)."""
    ccn = df['CCN']
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    sns.histplot(ccn, bins=range(1, 41), ax=ax, color='skyblue', kde=True)
    
    ax.set_title('Distribution of Cyclomatic Complexity (CCN)', fontsize=16)
    ax.set_xlabel('Cyclomatic Complexity (CCN)', fontsize=12)
    ax.set_ylabel('Number of Functions', fontsize=12)
    ax.set_xticks(range(1, 41, 2))
    ax.set_xlim(0, 40)

    # Add vertical lines for risk thresholds
    ax.axvline(10, color='orange', linestyle='--', linewidth=2, label='High Complexity (CCN > 10)')
    ax.axvline(20, color='red', linestyle='--', linewidth=2, label='Very High Complexity (CCN > 20)')
    ax.legend()
    
    save_plot(fig, output_path, '6_complexity_distribution.png')

def plot_top_complex_functions(df, output_path, top_n=20):
    """Visualizes the top N most complex functions."""
    top_complex = df.nlargest(top_n, 'CCN')
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    sns.barplot(x=top_complex['CCN'], y=top_complex['DisplayName'], ax=ax, palette='rocket')
    
    ax.set_title(f'Top {top_n} Most Complex Functions by CCN', fontsize=16)
    ax.set_xlabel('Cyclomatic Complexity (CCN)', fontsize=12)
    ax.set_ylabel('Function', fontsize=12)
    
    # Add data labels
    for i, (v, name) in enumerate(zip(top_complex['CCN'], top_complex['DisplayName'])):
        ax.text(v + 0.3, i, str(v), color='black', va='center')

    save_plot(fig, output_path, '7_top_complex_functions.png')

def plot_complexity_vs_loc(df, output_path):
    """Creates a scatter plot of Cyclomatic Complexity vs. Logical Lines of Code."""
    # Filter for functions with LOC > 0 to avoid plotting trivial cases
    df_filtered = df[(df['NLOC'] > 0) & (df['CCN'] > 0)]

    # Use a sample to avoid overplotting if the dataset is huge
    sample_df = df_filtered.sample(n=min(5000, len(df_filtered)), random_state=42)

    fig, ax = plt.subplots(figsize=(12, 8))
    
    sns.scatterplot(data=sample_df, x='NLOC', y='CCN', alpha=0.5, ax=ax, edgecolor='w')
    
    ax.set_title('Function Complexity (CCN) vs. Logical Lines of Code (lLOC)', fontsize=16)
    ax.set_xlabel('Logical Lines of Code (lLOC / NLOC)', fontsize=12)
    ax.set_ylabel('Cyclomatic Complexity (CCN)', fontsize=12)
    
    # Use log scales to better visualize wide-ranging data
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.xaxis.set_major_formatter(mticker.ScalarFormatter())
    ax.yaxis.set_major_formatter(mticker.ScalarFormatter())

    save_plot(fig, output_path, '8_complexity_vs_loc.png')

# --- Main Execution Logic ---

def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python visualize_complexity.py <path_to_complexity_report.csv>")
        
    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        sys.exit(f"Error: File not found at '{csv_path}'")
        
    results_dir = os.path.dirname(csv_path)
    output_plot_dir = os.path.join(results_dir, 'plots')
    
    print(f"Loading complexity data from: {csv_path}")
    complexity_df = load_complexity_data(csv_path)

    print("Generating complexity analysis plots...")
    
    plot_complexity_distribution(complexity_df, output_plot_dir)
    plot_top_complex_functions(complexity_df, output_plot_dir)
    plot_complexity_vs_loc(complexity_df, output_plot_dir)
    
    print("\nAll complexity plots generated successfully!")

if __name__ == '__main__':
    main()