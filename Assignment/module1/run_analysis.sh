#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_repo>"
    exit 1
fi

REPO_PATH=$1
REPO_NAME=$(basename "$REPO_PATH")
OUTPUT_DIR="results/$REPO_NAME"

mkdir -p "$OUTPUT_DIR"

CODEQL_CMD="/Users/lirongy/Workspace/codeql/codeql"

# echo "--- Analyzing LOC for $REPO_NAME ---"
# cloc "$REPO_PATH" --by-file --csv --out="$OUTPUT_DIR/loc_report.csv"

# echo "--- Analyzing Cyclomatic Complexity for $REPO_NAME ---"
# lizard "$REPO_PATH" -o "$OUTPUT_DIR/complexity_report.csv"

echo "--- Building CodeQL database for $REPO_NAME ---"
# change language here, default is c++
"$CODEQL_CMD" database create "$OUTPUT_DIR/${REPO_NAME}-db" \
    --language=cpp \
    --source-root="$REPO_PATH" \
    --no-build

echo "--- Running Fan-in / Fan-out analysis with CodeQL ---"
"$CODEQL_CMD" query run fanin-out.ql \
    --database="$OUTPUT_DIR/${REPO_NAME}-db" \
    --output="$OUTPUT_DIR/faninout.bqrs"

echo "--- Exporting Fan-in / Fan-out results to CSV ---"
"$CODEQL_CMD" bqrs decode "$OUTPUT_DIR/faninout.bqrs" \
    --format=csv \
    --output="$OUTPUT_DIR/faninout.csv"

echo "Analysis for $REPO_NAME complete. Results are in $OUTPUT_DIR"