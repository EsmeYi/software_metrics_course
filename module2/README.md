# Assignment 2: Software Measurement Systems

This repository contains solutions for Assignment 2, focusing on the design and implementation of software measurement systems.

- Part 1: A system for analyzing and predicting Defect Inflow, designed to meet the needs of a real Project Manager.
- Part 2: A system for measuring a custom, non-trivial metric, Self-Admitted Technical Debt (SATD), on a large source code repository.

---

## Part 1: Defect Inflow Prediction System

The analysis model is informed by input from a real-world Project Manager (Siyuan Zhang), who managed IBM Open XL C/C++ on Power compiler projects.

### System Design

The system follows a structured measurement workflow, separating collection, configuration, and analysis.

1. Stakeholder Input 
   Parameters and requirements were derived from a questionnaire (`Questionnaire_by_PM.pdf`).  
   Such as average effort per defect and risk thresholds.

2. Data Sources
   - Real Data: From upstream LLVM GitHub issues (PowerPC), via `fetch_llvm_issues.py`.
   - Simulated Data: Mock CSV (`mock_customer_defects.csv`) representing customer defect reports.

3. Analysis Model
   Defined entirely in `config.json`, including data inputs, effort units, risk thresholds, and prediction parameters.

4. Prediction Method 
   Uses Polynomial Regression, grouping historical defects by weekday to model weekly patterns.

5. Measures & Indicators
   - Base Measures: Daily/weekly `inflow` and `outflow`.
   - Derived Measures: Predicted inflow/outflow and weekly `predicted_workload` (Person-Days).
   - Indicator: `risk_level` (Green / Yellow / Red), based on weekly inflow.

### How to Run

#### Fetch Real Data (Optional)

```bash
export GITHUB_TOKEN="your_personal_access_token"

python fetch_llvm_issues.py
```

#### Run Analysis

```bash
python analyzer.py
```

### Assessment Criteria Coverage

* Raw Measures Visible: Outputs include `base_inflow_measures.csv`, `derived_predictions.csv`, `risk_indicators.csv`.
* Config-Based Model: `config.json` externalizes effort, thresholds, and prediction window.
* Flexible Inputs: Add/remove data via `input_data_files` in `config.json`.
* Change Prediction Horizon: Modify `weeks_to_predict`.

---

## Part 2: Self-Admitted Technical Debt (SATD) System 🛠️

This system measures a custom software quality metric: Self-Admitted Technical Debt (SATD), developer comments indicating postponed fixes.

### Design Overview

1. Metric Definition
   Counts comments containing `TODO:`, `FIXME:`, `HACK:`, `XXX:`.

2. Target Repository
   The LLVM Project. Each measured entity corresponds to a top-level module (`clang`, `llvm`, `mlir`, etc.).

3. Measurement Instrument
   `measure_system.py` scans a local LLVM clone using SATD patterns defined in `config.json`.

4. Measures & Indicators

   * Raw Data: Logged in `raw_satd_data.csv`.
   * Base Measure: `satd_count` per module.
   * Derived Measure: `debt_density` = SATD / number of files.
   * Indicator: `risk_level` (High / Medium / Low).

### How to Run

#### Setup

```bash
git clone https://github.com/llvm/llvm-project.git
```

#### Configure

Edit `part2/config.json`.
Modify `modules_to_scan` to choose 1 or many modules.

#### Measure

```bash
python measure_system.py
```

### Assessment Criteria Coverage

* Metric Chosen: SATD reflects code health.
* Instrument Created: `measure_system.py`.
* Visualization: Outputs `satd_distribution_chart.png` (bar chart per module).
