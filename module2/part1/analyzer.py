# inflow_analyzer.py (Weekly Visualization Version)
import pandas as pd
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import sys
from datetime import datetime, date, timedelta

def load_config(config_path='config.json'):
    """Loads the main configuration file and returns the analysis settings section."""
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found.")
        return None
    with open(config_path, 'r') as f:
        return json.load(f).get("analysis_settings")

def predict_daily_polynomial(daily_history, predict_days):
    """
    Predicts future daily defect counts using polynomial regression.
    The core logic remains daily to capture weekly patterns.
    """
    hist_by_weekday = [[] for _ in range(7)]
    function_by_weekday = [None] * 7
    
    today = date.today()
    for i, count in enumerate(daily_history):
        current_date = today - timedelta(days=(len(daily_history) - i))
        weekday = current_date.weekday()
        hist_by_weekday[weekday].append(count)

    for wd in range(7):
        y = hist_by_weekday[wd]
        y.reverse()
        x = range(-len(y), 0)
        
        if len(y) < 4:
            avg = np.mean(y) if y else 0
            function_by_weekday[wd] = np.poly1d([avg])
        else:
            coeffs = np.polyfit(x, y, deg=3)
            function_by_weekday[wd] = np.poly1d(coeffs)

    pred_y = [0] * predict_days
    for i in range(predict_days):
        future_date = today + timedelta(days=i + 1)
        weekday = future_date.weekday()
        week_index = i // 7
        prediction = function_by_weekday[weekday](week_index)
        pred_y[i] = max(prediction, 0)
        
    return pred_y

def analyze_inflow_outflow(config):
    """
    Main analysis function. It performs daily calculations in the background
    but prepares weekly aggregated data for visualization.
    """
    if not config: return None, None, None

    # --- Step 1: Load and combine data (no changes) ---
    input_files = config.get('input_data_files', [])
    all_dataframes = []
    print("--- Loading and combining data sources ---")
    for file_path in input_files:
        if os.path.exists(file_path):
            print(f"Reading file: {file_path}")
            if os.path.getsize(file_path) > 0:
                all_dataframes.append(pd.read_csv(file_path))
        else:
            print(f"Warning: Data file '{file_path}' not found.")
    if not all_dataframes:
        print("Error: No valid data files found.")
        return None, None, None
    RAW_DATA = pd.concat(all_dataframes, ignore_index=True)
    
    # --- Step 2: Prepare data (no changes) ---
    RAW_DATA['creation_date'] = pd.to_datetime(RAW_DATA['creation_date'], format='mixed')
    RAW_DATA['updated_at'] = pd.to_datetime(RAW_DATA['updated_at'], format='mixed')
    print(f"Data loading complete. Found {len(RAW_DATA)} total records.")
    
    # --- Step 3: Calculate daily base measures (for internal calculation) ---
    daily_new = RAW_DATA.set_index('creation_date').resample('D').size()
    daily_resolved = RAW_DATA[RAW_DATA['status'] == 'closed'].set_index('updated_at').resample('D').size()
    
    daily_base_measures_df = pd.merge(daily_new.rename('inflow'), daily_resolved.rename('outflow'), 
                                left_index=True, right_index=True, how='outer').fillna(0).astype(int)
    
    all_days_index = pd.date_range(start=daily_base_measures_df.index.min(), end=date.today(), freq='D')
    daily_base_measures_df = daily_base_measures_df.reindex(all_days_index, fill_value=0)
    
    # --- Aggregate daily data to weekly for visualization and reporting ---
    weekly_base_measures_df = daily_base_measures_df.resample('W-MON').sum().reset_index()
    weekly_base_measures_df.rename(columns={'index': 'week_start_date'}, inplace=True)
    print("\n--- Weekly Base Measures (for visualization) ---")
    print(weekly_base_measures_df.tail())
    weekly_base_measures_df.to_csv(config['output_files']['base_measures'], index=False)
    
    # --- Step 4: Perform daily prediction (for accuracy) ---
    PREDICT_DAYS = config['weeks_to_predict'] * 7
    daily_new_list = daily_base_measures_df['inflow'].tolist()
    daily_resolved_list = daily_base_measures_df['outflow'].tolist()
    
    pnew_y_daily = predict_daily_polynomial(daily_new_list, PREDICT_DAYS)
    presolved_y_daily = predict_daily_polynomial(daily_resolved_list, PREDICT_DAYS)
    
    # --- Aggregate daily predictions to weekly predictions ---
    predicted_inflow_weekly = [sum(pnew_y_daily[i:i+7]) for i in range(0, len(pnew_y_daily), 7)]
    predicted_outflow_weekly = [sum(presolved_y_daily[i:i+7]) for i in range(0, len(presolved_y_daily), 7)]
    
    effort_per_defect = config['effort_per_defect']
    effort_unit = config['effort_unit']
    predicted_workload_weekly = [round(p * effort_per_defect, 2) for p in predicted_inflow_weekly]
    
    last_hist_date = weekly_base_measures_df['week_start_date'].max()
    pred_dates_weekly = [last_hist_date + timedelta(weeks=i+1) for i in range(config['weeks_to_predict'])]
    
    derived_measures_df = pd.DataFrame({
        'prediction_week_start': pred_dates_weekly,
        'predicted_inflow': predicted_inflow_weekly,
        'predicted_outflow': predicted_outflow_weekly,
        f'predicted_workload_{effort_unit.lower()}': predicted_workload_weekly
    })
    print("\n--- Weekly Derived Measures (Predictions) ---")
    print(derived_measures_df)
    derived_measures_df.to_csv(config['output_files']['derived_measures'], index=False)
    
    # --- Step 5: Generate indicators (based on average weekly inflow) ---
    average_predicted_weekly_inflow = np.mean(predicted_inflow_weekly) if predicted_inflow_weekly else 0
    thresholds = config['inflow_thresholds']
    
    if average_predicted_weekly_inflow > thresholds['red_alert_gt']:
        indicator_color = 'red'
    elif average_predicted_weekly_inflow < thresholds['yellow_warning_eq']:
        indicator_color = 'green'
    else:
        indicator_color = 'yellow'
        
    indicators_df = pd.DataFrame([{'average_predicted_weekly_inflow': round(average_predicted_weekly_inflow, 2), 'risk_level': indicator_color.upper()}])
    print("\n--- Indicators (based on predicted weekly average inflow) ---")
    print(indicators_df)
    indicators_df.to_csv(config['output_files']['indicators'], index=False)

    return weekly_base_measures_df, derived_measures_df, indicator_color

def visualize(weekly_base_df, weekly_derived_df, indicator_color, config):
    """Generates the final charts using weekly aggregated data."""
    plt.figure(figsize=(15, 6))
    
    # The x-axis is now based on weeks
    x_axis_history = list(range(-len(weekly_base_df), 0))
    x_axis_predicted = list(range(len(weekly_derived_df)))
    
    plt.plot(x_axis_history, weekly_base_df['inflow'], label="Historical Inflow (Weekly)", color='blue', marker='o', linestyle='-')
    plt.plot(x_axis_history, weekly_base_df['outflow'], label="Historical Outflow (Weekly)", color='green', marker='x', linestyle='-')
    plt.plot(x_axis_predicted, weekly_derived_df['predicted_inflow'], label="Predicted Inflow (Weekly)", color='red', marker='o', linestyle='--')
    plt.plot(x_axis_predicted, weekly_derived_df['predicted_outflow'], label="Predicted Outflow (Weekly)", color='orange', marker='x', linestyle='--')
    
    if x_axis_predicted:
        plt.axvspan(x_axis_predicted[0] - 0.5, x_axis_predicted[-1] + 0.5, color=indicator_color, alpha=0.2, label=f"Health Status: {indicator_color.upper()}")
    
    plt.title("Defect Inflow vs. Outflow (Weekly View): History and Prediction", fontsize=16)
    plt.xlabel("Weeks from Today (0 = Next Week)")
    plt.ylabel("Number of Defects per Week")
    plt.legend()
    plt.grid(True, which='both', linestyle='--', alpha=0.6)
    
    chart_filename = config['output_files']['chart']
    plt.savefig(chart_filename)
    print(f"\nMain chart saved as {chart_filename}")
    plt.show()

    # Dashboard indicator (no changes needed)
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.set_facecolor(indicator_color)
    ax.tick_params(axis='both', which='both', bottom=False, top=False, left=False, right=False, 
                   labelbottom=False, labelleft=False)
    ax.set_title(f"Project Health: {indicator_color.upper()}", fontsize=14)
    plt.show()

if __name__ == '__main__':
    analysis_config = load_config()
    if analysis_config:
        weekly_base, weekly_derived, indicator = analyze_inflow_outflow(analysis_config)
        if weekly_base is not None and weekly_derived is not None:
            visualize(weekly_base, weekly_derived, indicator, analysis_config)
