import sys
import os
import csv
from collections import defaultdict
from clang.cindex import Index, CursorKind

# C/C++
SUPPORTED_EXTENSIONS = ['.c', '.cpp', '.h', '.hpp']


def find_source_files(directory):
    source_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                source_files.append(os.path.join(root, file))
    return source_files


def get_defined_functions(source_files):
    defined_functions = set()
    index = Index.create()
    
    print(f"Pass 1: Finding all function definitions in {len(source_files)} files...")
    
    for i, filepath in enumerate(source_files):
        try:
            tu = index.parse(filepath)
            for cursor in tu.cursor.walk_preorder():
                if cursor.kind == CursorKind.FUNCTION_DECL and cursor.is_definition():
                    defined_functions.add(cursor.spelling)
        except Exception as e:
            pass
            
        if (i + 1) % 100 == 0:
            print(f"  ...processed {i+1}/{len(source_files)} files")

    print(f"Found {len(defined_functions)} function definitions.")
    return defined_functions


def build_call_graph(source_files, defined_functions):
    call_graph = defaultdict(set)
    index = Index.create()
    
    print(f"Pass 2: Building call graph from {len(source_files)} files...")
    
    for i, filepath in enumerate(source_files):
        try:
            tu = index.parse(filepath)
            
            current_function_stack = []
            
            for cursor in tu.cursor.walk_preorder():
                if cursor.kind == CursorKind.FUNCTION_DECL and cursor.is_definition():
                    current_function_stack.append(cursor.spelling)
                
                elif cursor.kind == CursorKind.CALL_EXPR and current_function_stack:
                    caller_name = current_function_stack[-1]
                    callee_name = cursor.spelling
                    
                    if callee_name in defined_functions:
                        call_graph[caller_name].add(callee_name)
                
                elif cursor.kind == CursorKind.COMPOUND_STMT and current_function_stack:
                    if len(list(cursor.get_children())) > 0:
                        parent = list(cursor.get_children())[0].lexical_parent
                        if parent.kind == CursorKind.FUNCTION_DECL:
                             current_function_stack.pop()
        except Exception as e:
            # print(f"Warning: Could not parse {filepath}: {e}")
            pass
            
        if (i + 1) % 100 == 0:
            print(f"  ...processed {i+1}/{len(source_files)} files")
            
    return call_graph


def main():
    if len(sys.argv) != 2:
        print("Usage: python calculate_fan.py <path_to_repo>")
        sys.exit(1)
        
    repo_path = sys.argv[1]
    if not os.path.isdir(repo_path):
        print(f"Error: Directory not found at '{repo_path}'")
        sys.exit(1)

    source_files = find_source_files(repo_path)
    if not source_files:
        print("No C/C++ source files found.")
        sys.exit(0)

    defined_functions = get_defined_functions(source_files)
    
    call_graph = build_call_graph(source_files, defined_functions)

    # Fan-out
    fan_out = {func: len(callees) for func, callees in call_graph.items()}

    # Fan-in
    fan_in = defaultdict(int)
    for caller, callees in call_graph.items():
        for callee in callees:
            fan_in[callee] += 1
            
    writer = csv.writer(sys.stdout)
    writer.writerow(['function_name', 'fan_in', 'fan_out'])
    
    all_functions = sorted(list(defined_functions))
    
    for func_name in all_functions:
        fi = fan_in.get(func_name, 0)
        fo = fan_out.get(func_name, 0)
        writer.writerow([func_name, fi, fo])

    print("Fan-in/Fan-out analysis complete.")

if __name__ == "__main__":
    main()