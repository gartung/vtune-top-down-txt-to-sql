#!/usr/bin/env python3
"""
Extract immediate children of edm::stream::EDProducerAdaptorBase::doEvent
from a top-down profiling CSV file.
"""

import sys
import csv


def count_leading_spaces(line):
    """Count the number of leading spaces in a line."""
    count = 0
    for char in line:
        if char == ' ':
            count += 1
        else:
            break
    return count


def get_total_cpu_time(filename):
    """
    Get the total CPU time from the first data line.
    
    Args:
        filename: Path to the CSV file
    
    Returns:
        float: Total CPU time
    """
    with open(filename, 'r', encoding='utf-8') as f:
        # Skip the header lines
        for line in f:
            if line.startswith('Function Stack;'):
                break
        
        # Read the first data line (Total)
        for line in f:
            if line.strip():
                parts = line.split(';')
                if len(parts) >= 2:
                    try:
                        return float(parts[1])
                    except ValueError:
                        return 0.0
    return 0.0


def extract_immediate_children(filename, parent_function):
    """
    Extract all immediate children of a given parent function.
    
    Args:
        filename: Path to the CSV file
        parent_function: The function name to find children for
    
    Returns:
        List of tuples: (full_function_call, total_time)
    """
    children = []
    parent_indent = None
    found_parent = False
    
    with open(filename, 'r', encoding='utf-8') as f:
        # Skip the header lines
        for line in f:
            if line.startswith('Function Stack;'):
                break
        
        # Process the data lines
        for line in f:
            # Skip empty lines
            if not line.strip():
                continue
            
            # Parse the line
            parts = line.split(';')
            if len(parts) < 4:
                continue
            
            function_stack = parts[0]
            total_time = parts[1]
            # self_time = parts[2]
            full_function = parts[3].strip()
            
            # Count leading spaces
            indent = count_leading_spaces(function_stack)
            
            # Check if this is the parent function we're looking for
            if parent_function in function_stack and not found_parent:
                parent_indent = indent
                found_parent = True
                continue
            
            # If we found the parent, look for immediate children
            if found_parent and parent_indent is not None:
                # Immediate children have exactly one more level of indentation
                if indent == parent_indent + 1:
                    children.append((full_function, total_time))
                # If we encounter a function at the same or lower level, we're done
                elif indent <= parent_indent:
                    break
    
    return children


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_children.py <csv_file>")
        sys.exit(1)
    
    filename = sys.argv[1]
    parent_function = "edm::stream::EDProducerAdaptorBase::doEvent"
    
    print(f"Extracting immediate children of: {parent_function}\n")
    
    children = extract_immediate_children(filename, parent_function)
    
    if not children:
        print("No children found.")
        return
    
    print(f"Found {len(children)} immediate children:\n")
    print("-" * 100)
    
    for full_function, total_time in children:
        print(f"{full_function}  {total_time}")
    
    print("-" * 100)
    print(f"\nTotal: {len(children)} functions")


if __name__ == "__main__":
    main()
