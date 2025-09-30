#!/bin/bash

# Usage: ./run_analysis.sh <path_to_repo> <language>
# Example: ./run_analysis.sh ./linux cpp
#          ./run_analysis.sh ./kafka java

if [ $# -lt 2 ]; then
    echo "Usage: $0 <path_to_repo> <language>"
    exit 1
fi

REPO_PATH=$1
LANGUAGE=$2
REPO_NAME=$(basename "$REPO_PATH")
OUTPUT_DIR="results/$REPO_NAME"
mkdir -p "$OUTPUT_DIR"

echo "--- Analyzing LOC for $REPO_NAME ---"
cloc "$REPO_PATH" --by-file --csv --out="$OUTPUT_DIR/loc_report.csv"

echo "--- Analyzing Cyclomatic Complexity for $REPO_NAME ---"
lizard "$REPO_PATH" -o "$OUTPUT_DIR/complexity_report.csv"

# DB_PATH="$OUTPUT_DIR/${REPO_NAME}-db"
# QUERY_DIR="./codeql-queries/$LANGUAGE/fanin-out.ql"

# echo "--- Building CodeQL database for $REPO_NAME (language=$LANGUAGE) ---"
# if [ "$LANGUAGE" = "cpp" ]; then
#     # C/C++
#     codeql database create "$DB_PATH" \
#         --language=cpp \
#         --source-root="$REPO_PATH" \
#         --command="make -j$(nproc)" \
#         --overwrite
# elif [ "$LANGUAGE" = "java" ]; then
#     # Java
#     codeql database create "$DB_PATH" \
#         --language=java \
#         --source-root="$REPO_PATH" \
#         --command="./build.sh" \
#         --overwrite
# else
#     # Python
#     codeql database create "$DB_PATH" \
#         --language="$LANGUAGE" \
#         --source-root="$REPO_PATH" \
#         --overwrite
# fi

# echo "--- Running Fan-in / Fan-out analysis with CodeQL ---"
# if [ ! -f "$QUERY_DIR" ]; then
#     echo "Error: Query file $QUERY_DIR not found!"
#     exit 1
# fi
# codeql query run "$QUERY_DIR" \
#     --database="$DB_PATH" \
#     --output="$OUTPUT_DIR/faninout.bqrs"

# echo "--- Exporting Fan-in / Fan-out results to CSV ---"
# codeql bqrs decode "$OUTPUT_DIR/faninout.bqrs" \
#     --format=csv \
#     --output="$OUTPUT_DIR/faninout.csv"

echo "Analysis for $REPO_NAME complete. Results are in $OUTPUT_DIR"
