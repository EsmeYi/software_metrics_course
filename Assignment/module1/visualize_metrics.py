# visualize_metrics.py

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as mticker

# --- Configuration for Plot Aesthetics ---
def setup_plot_style():
    """Sets global matplotlib and seaborn styles for consistent plots."""
    sns.set_style("whitegrid")
    plt.rcParams.update({
        'figure.titlesize': 20,      # Figure title
        'axes.titlesize': 18,        # Subplot title
        'axes.labelsize': 16,        # X and Y labels
        'xtick.labelsize': 16,       # X-axis tick labels
        'ytick.labelsize': 16,       # Y-axis tick labels
        'legend.fontsize': 16,       # Legend font size
        'font.family': 'sans-serif'  # A clean, modern font
    })
# -----------------------------------------

def save_plot(fig, output_path, filename):
    """Saves a matplotlib figure to a specified path."""
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    full_path = os.path.join(output_path, filename)
    fig.savefig(full_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {full_path}")
    plt.close(fig)

def get_module_from_path(path, repo_name, depth=1):
    """Extracts the module name from a file path."""
    clean_path = str(path)
    if clean_path.startswith('./'):
        clean_path = clean_path[2:]
    
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

def load_data(results_dir):
    """Loads all three CSV files from a results directory."""
    loc_path = os.path.join(results_dir, 'loc_report.csv')
    comp_path = os.path.join(results_dir, 'complexity_report.csv')
    fan_path = os.path.join(results_dir, 'faninout.csv')
    
    if not all(os.path.exists(p) for p in [loc_path, comp_path, fan_path]):
        sys.exit(f"Error: One or more required CSV files not found in '{results_dir}'")
        
    loc_df = pd.read_csv(loc_path)
    
    numeric_cols = ['blank', 'comment', 'code']
    for col in numeric_cols:
        loc_df[col] = pd.to_numeric(loc_df[col], errors='coerce')
    loc_df[numeric_cols] = loc_df[numeric_cols].fillna(0)

    if 'SUM' in loc_df['language'].values:
        loc_df = loc_df[loc_df['language'] != 'SUM'].copy()

    comp_col_names = [
        'NLOC', 'CCN', 'Token', 'Parameters', 'Length', 'Location', 
        'FilePath', 'FunctionName', 'FullSignature', 'StartLine', 'EndLine'
    ]
    comp_df = pd.read_csv(comp_path, header=None, names=comp_col_names)
    
    fan_df = pd.read_csv(fan_path)
    fan_df.columns = ['caller', 'relation', 'callee']

    return loc_df, comp_df, fan_df

def plot_repo_summary(loc_df, comp_df, fan_df, output_path):
    """Creates a dashboard-like plot for the entire repository."""
    total_ploc = loc_df['blank'].sum() + loc_df['comment'].sum() + loc_df['code'].sum()
    total_lloc = comp_df['NLOC'].sum()
    avg_ccn = comp_df['CCN'].mean()
    
    fan_out = fan_df.groupby('caller').size()
    fan_in = fan_df.groupby('callee').size()
    avg_fan_out = fan_out.mean()
    avg_fan_in = fan_in.mean()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis('off')
    
    repo_name = os.path.basename(os.path.dirname(output_path))
    # Note: fig.suptitle font size is controlled by 'figure.titlesize' in rcParams
    fig.suptitle(f'Repository Summary: {repo_name}', weight='bold')
    
    metrics_text = (
        f"Lines of Code\n"
        f"-----------------------------\n"
        f"Physical (pLOC): {total_ploc:,.0f}\n"
        f"Logical (lLOC): {total_lloc:,.0f}\n\n"
        f"Complexity & Coupling\n"
        f"-----------------------------\n"
        f"Average McCabe (CCN): {avg_ccn:.2f}\n"
        f"Average Fan-in: {avg_fan_in:.2f}\n"
        f"Average Fan-out: {avg_fan_out:.2f}\n"
    )
    
    # Text-specific fontsize remains here, as it's not a standard chart element
    ax.text(0.5, 0.5, metrics_text, ha='center', va='center', fontsize=14, 
            fontfamily='monospace', bbox=dict(boxstyle="round,pad=1", fc='skyblue', alpha=0.1))

    save_plot(fig, output_path, '0_repo_summary.pdf')

def plot_loc_comparison_per_module(loc_df, comp_df, repo_name, output_path, top_n=15):
    """Plots a grouped bar chart of pLOC vs lLOC for top modules."""
    loc_df['pLOC'] = loc_df['blank'] + loc_df['comment'] + loc_df['code']
    loc_df['module'] = loc_df['filename'].apply(lambda p: get_module_from_path(p, repo_name, depth=1))
    ploc_by_module = loc_df.groupby('module')['pLOC'].sum().reset_index()

    comp_df['module'] = comp_df['FilePath'].apply(lambda p: get_module_from_path(p, repo_name, depth=1))
    lloc_by_module = comp_df.groupby('module')['NLOC'].sum().reset_index()
    lloc_by_module.rename(columns={'NLOC': 'lLOC'}, inplace=True)
    
    merged_df = pd.merge(ploc_by_module, lloc_by_module, on='module', how='outer').fillna(0)
    merged_df = merged_df[merged_df['module'] != '(Root)'].nlargest(top_n, 'pLOC')
    
    plot_df = merged_df.melt(id_vars='module', var_name='LOC_Type', value_name='Lines')

    fig, ax = plt.subplots(figsize=(14, 8))
    sns.barplot(data=plot_df, x='Lines', y='module', hue='LOC_Type', ax=ax)

    # Note: Font sizes are now handled by the global rcParams settings
    ax.set_title('')
    ax.set_xlabel('Lines of Code')
    ax.set_ylabel('Module')
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: format(int(x), ',')))

    save_plot(fig, output_path, '1_loc_per_module.pdf')

def plot_complexity_per_module(comp_df, repo_name, output_path, top_n=10):
    """Plots a box plot of CCN distribution per module."""
    comp_df['module'] = comp_df['FilePath'].apply(lambda p: get_module_from_path(p, repo_name, depth=1))
    
    top_modules = comp_df.groupby('module')['NLOC'].sum().nlargest(top_n).index
    plot_df = comp_df[comp_df['module'].isin(top_modules)]
    
    fig, ax = plt.subplots(figsize=(14, 8))
    sns.boxplot(data=plot_df, y='module', x='CCN', ax=ax, orient='h', palette='coolwarm')
    
    # Note: Font sizes are now handled by the global rcParams settings
    ax.set_title('')
    ax.set_xlabel('Cyclomatic Complexity (CCN)')
    ax.set_ylabel('Module')
    ax.set_xscale('log') 
    ax.xaxis.set_major_formatter(mticker.ScalarFormatter())

    save_plot(fig, output_path, '2_complexity_per_module.pdf')

def plot_fan_metrics(fan_df, output_path, top_n=20):
    """Generates three plots for fan-in and fan-out."""
    fan_out = fan_df.groupby('caller').size().reset_index(name='fan_out')
    fan_in = fan_df.groupby('callee').size().reset_index(name='fan_in')
    
    # 1. Top N Fan-out
    top_fan_out = fan_out.nlargest(top_n, 'fan_out')
    fig1, ax1 = plt.subplots(figsize=(12, 10))
    sns.barplot(data=top_fan_out, x='fan_out', y='caller', ax=ax1, palette='rocket')
    ax1.set_title('')
    ax1.set_xlabel('Fan-Out Count')
    ax1.set_ylabel('Function')
    save_plot(fig1, output_path, '3_top_fan_out.pdf')

    # 2. Top N Fan-in
    top_fan_in = fan_in.nlargest(top_n, 'fan_in')
    fig2, ax2 = plt.subplots(figsize=(12, 10))
    sns.barplot(data=top_fan_in, x='fan_in', y='callee', ax=ax2, palette='mako')
    ax2.set_title('')
    ax2.set_xlabel('Fan-In Count')
    ax2.set_ylabel('Function')
    save_plot(fig2, output_path, '4_top_fan_in.pdf')

    # 3. Fan-in vs Fan-out Scatter Plot
    merged_fan = pd.merge(fan_in.rename(columns={'callee': 'function'}), 
                          fan_out.rename(columns={'caller': 'function'}), 
                          on='function', how='outer').fillna(0)
    
    sample_df = merged_fan.sample(n=min(5000, len(merged_fan)), random_state=42)
    fig3, ax3 = plt.subplots(figsize=(12, 8))
    sns.scatterplot(data=sample_df, x='fan_out', y='fan_in', alpha=0.6, ax=ax3, edgecolor=None)
    ax3.set_title('')
    ax3.set_xlabel('Fan-Out (Outgoing Calls)')
    ax3.set_ylabel('Fan-In (Incoming Calls)')
    ax3.set_xscale('log')
    ax3.set_yscale('log')
    save_plot(fig3, output_path, '5_fanin_vs_fanout.pdf')


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python visualize_metrics.py <path_to_results_directory>")
    
    # --- Set the global plot style and font sizes ---
    setup_plot_style()
    
    results_dir = sys.argv[1]
    repo_name = os.path.basename(results_dir)
    output_plot_dir = os.path.join(results_dir, 'plots')
    
    print("--- Loading Data ---")
    loc_df, comp_df, fan_df = load_data(results_dir)
    
    print("\n--- Generating Plots ---")
    plot_repo_summary(loc_df, comp_df, fan_df, output_plot_dir)
    plot_loc_comparison_per_module(loc_df, comp_df, repo_name, output_plot_dir)
    plot_complexity_per_module(comp_df, repo_name, output_plot_dir)
    plot_fan_metrics(fan_df, output_plot_dir)
    
    print("\n--- All visualizations generated successfully! ---")

if __name__ == '__main__':
    main()