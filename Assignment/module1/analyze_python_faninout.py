import ast
import os
import csv
from collections import defaultdict

REPO_PATH = "./nova"
OUTPUT_CSV = "./results/nova/faninout.csv"

calls_from = defaultdict(set)
calls_to = defaultdict(set)

def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except Exception as e:
            print(f"Skipping {filepath} due to parse error: {e}")
            return

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            for n in ast.walk(node):
                if isinstance(n, ast.Call):
                    if isinstance(n.func, ast.Name):
                        called_name = n.func.id
                        calls_from[func_name].add(called_name)
                        calls_to[called_name].add(func_name)
                    elif isinstance(n.func, ast.Attribute):
                        called_name = n.func.attr
                        calls_from[func_name].add(called_name)
                        calls_to[called_name].add(func_name)

for root, dirs, files in os.walk(REPO_PATH):
    for file in files:
        if file.endswith(".py"):
            process_file(os.path.join(root, file))

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["caller", "col1", "callee"])
    for caller, callees in calls_from.items():
        for callee in callees:
            writer.writerow([caller, "calls", callee])

print(f"Fan-in/Fan-out CSV exported to {OUTPUT_CSV}")

