# Software Metrics Analysis

This repository contains scripts to perform software metrics analysis (Lines of Code, Cyclomatic Complexity, Fan-in/Fan-out) on multiple repositories written in C/C++ (linux), Java (kafka), and Python (openstack).

---

## Repository Structure

```
.
├── run_analysis.sh                  # Bash script to run the full analysis pipeline
├── visualize_metrics.py             # Python script to generate plots from metrics CSVs
├── analyze_python_faninout.py       # Python script to compute Fan-in/Fan-out for Python repos
├── codeql-queries                   # CodeQL queries for different languages
│   ├── cpp
│   │   ├── fanin-out.ql
│   │   └── qlpack.yml
│   ├── java
│   │   ├── fanin-out.ql
│   │   └── qlpack.yml
│   └── python
│       ├── fanin-out.ql
│       └── qlpack.yml
├── results                          # Stores analysis results and plots
│   ├── kafka
│   ├── linux
│   └── nova
└── README.md

```

---

## Usage

### Requirements

Ensure the following tools are installed:

- **Python**
- **cloc** (for LOC)
- **lizard** (for Cyclomatic Complexity)
- **CodeQL CLI** (for fan-in/fan-out)
- Required dependencies for analyzed projects

### Clone Repositories

Before running the analysis, clone the target repositories:

```
git clone --depth=1 https://github.com/torvalds/linux.git

git clone --depth=1 https://github.com/apache/kafka.git

git clone --depth=1 https://github.com/openstack/nova.git
```

### Run Analysis on a Repository

```
./run_analysis.sh <path_to_repo> <language>
```

* `<path_to_repo>`: Local path to the repository to analyze
* `<language>`: `cpp`, `java`, or `python`

Example:

```
./run_analysis.sh ./kafka java
```

The script performs the following:

1. Computes Lines of Code using **cloc**
2. Computes Cyclomatic Complexity using **lizard**
3. Builds a **CodeQL database** for Fan-in/Fan-out analysis
4. Runs **Fan-in/Fan-out queries** using CodeQL
5. Exports all metrics to CSV in `results/<repo_name>/`

#### Notes

For Python repositories, the `analyze_python_faninout.py` script handles static function call extraction instead of CodeQL.

```bash
python analyze_python_faninout.py
```

### Visualize Metrics

After running the analysis, generate visualizations:

```bash
python visualize_metrics.py
```


### Example Results

```text
results/linux/
├── loc_report.csv
├── complexity_report.csv
├── faninout.csv
└── plots/
    ├── 0_repo_summary.png
    ├── 1_loc_per_module.png
    ├── 2_complexity_per_module.png
    ├── 3_top_fan_out.png
    ├── 4_top_fan_in.png
    └── 5_fanin_vs_fanout.png
```

---
## Metrics Definitions

### 1. Lines of Code (LOC)

- **Physical LOC (PLOC)**
  - Definition: Total number of lines in the file, including code and comments, excluding blank lines.
  - Tool: `cloc`

- **Logical LOC (LLOC)**  
  - Definition: Number of executable statements, ignoring formatting and line breaks.  
  - Tool: `lizard`
  - Counting rules: 
    - Multiple statements on a single line counted as 1 LLOC
    - A single statement spanning multiple lines counted as 1 LLOC

### 2. McCabe Cyclomatic Complexity (CCN)

- Definition: Number of independent paths through a function; measures the complexity of control flow.  
- Tool: `lizard`

### 3. Fan-in

- Definition: Number of distinct functions that **call a given function** (incoming dependencies).  
- Tool: `CodeQL`

### 4. Fan-out

- Definition: Number of distinct functions **called by a given function** (outgoing dependencies).  
- Tool: `CodeQL`

## References

* [CodeQL CLI Documentation](https://codeql.github.com/docs/codeql-cli/)
* [cloc](https://github.com/AlDanial/cloc)
* [lizard](https://github.com/terryyin/lizard)
