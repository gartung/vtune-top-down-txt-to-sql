#!/usr/bin/env python3
"""
Convert top-down profiling CSV file to SQLite database.
Creates tables for functions and their call relationships.
"""

import sys
import sqlite3
import hashlib


def count_leading_spaces(line):
    """Count the number of leading spaces in a line."""
    count = 0
    for char in line:
        if char == ' ':
            count += 1
        else:
            break
    return count


def generate_function_id(full_function, indent_level):
    """Generate a unique ID for a function based on its signature and level."""
    # Use hash of function name and indent to create unique ID
    hash_obj = hashlib.md5(f"{full_function}_{indent_level}".encode())
    return hash_obj.hexdigest()[:16]


def parse_csv_to_database(csv_file, db_file):
    """
    Parse CSV file and create SQLite database.
    
    Args:
        csv_file: Path to input CSV file
        db_file: Path to output SQLite database
    """
    # Connect to SQLite database (creates if doesn't exist)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS functions (
            id TEXT PRIMARY KEY,
            function_stack TEXT NOT NULL,
            short_name TEXT NOT NULL,
            full_signature TEXT NOT NULL,
            total_time REAL NOT NULL,
            self_time REAL NOT NULL,
            percentage REAL NOT NULL,
            indent_level INTEGER NOT NULL,
            line_number INTEGER NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS call_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id TEXT,
            child_id TEXT NOT NULL,
            FOREIGN KEY (parent_id) REFERENCES functions(id),
            FOREIGN KEY (child_id) REFERENCES functions(id)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_parent ON call_relationships(parent_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_child ON call_relationships(child_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_indent ON functions(indent_level)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_percentage ON functions(percentage)
    ''')
    
    # First pass: get total CPU time from first data line
    total_cpu_time = 0.0
    with open(csv_file, 'r', encoding='utf-8') as f:
        # Skip header lines
        for line in f:
            if line.startswith('Function Stack;'):
                break
        
        # Read first data line (Total)
        for line in f:
            if line.strip():
                parts = line.split(';')
                if len(parts) >= 2:
                    try:
                        total_cpu_time = float(parts[1])
                    except ValueError:
                        total_cpu_time = 1.0  # Avoid division by zero
                break
    
    if total_cpu_time == 0.0:
        total_cpu_time = 1.0  # Avoid division by zero
    
    # Parse CSV file
    parent_stack = []  # Stack to track parent functions at each level
    line_number = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        # Skip header lines
        for line in f:
            line_number += 1
            if line.startswith('Function Stack;'):
                break
        
        # Process data lines
        for line in f:
            line_number += 1
            
            # Skip empty lines
            if not line.strip():
                continue
            
            # Parse the line
            parts = line.split(';')
            if len(parts) < 4:
                continue
            
            function_stack = parts[0]
            total_time_str = parts[1]
            self_time_str = parts[2]
            full_signature = parts[3].strip()
            
            # Extract short name from function stack
            short_name = function_stack.strip()
            
            # Count indent level
            indent_level = count_leading_spaces(function_stack)
            
            # Parse times
            try:
                total_time = float(total_time_str)
            except ValueError:
                total_time = 0.0
            
            try:
                self_time = float(self_time_str)
            except ValueError:
                self_time = 0.0
            
            # Generate unique ID
            func_id = generate_function_id(full_signature, line_number)
            
            # Calculate percentage
            percentage = (total_time / total_cpu_time * 100.0) if total_cpu_time > 0 else 0.0
            
            # Insert function into database
            cursor.execute('''
                INSERT OR REPLACE INTO functions 
                (id, function_stack, short_name, full_signature, total_time, self_time, percentage, indent_level, line_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (func_id, function_stack, short_name, full_signature, total_time, self_time, percentage, indent_level, line_number))
            
            # Update parent stack
            # Remove parents at same or higher indent level
            while parent_stack and parent_stack[-1][1] >= indent_level:
                parent_stack.pop()
            
            # Add relationship to parent if exists
            if parent_stack:
                parent_id = parent_stack[-1][0]
                cursor.execute('''
                    INSERT INTO call_relationships (parent_id, child_id)
                    VALUES (?, ?)
                ''', (parent_id, func_id))
            else:
                # Root level function - no parent
                cursor.execute('''
                    INSERT INTO call_relationships (parent_id, child_id)
                    VALUES (?, ?)
                ''', (None, func_id))
            
            # Add current function to parent stack
            parent_stack.append((func_id, indent_level))
    
    # Commit and close
    conn.commit()
    
    # Print statistics
    cursor.execute('SELECT COUNT(*) FROM functions')
    func_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM call_relationships')
    rel_count = cursor.fetchone()[0]
    
    print(f"Database created: {db_file}")
    print(f"  Total CPU time: {total_cpu_time}")
    print(f"  Functions: {func_count}")
    print(f"  Relationships: {rel_count}")
    
    conn.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python csv_to_sql.py <csv_file> [output_db_file]")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    db_file = sys.argv[2] if len(sys.argv) > 2 else csv_file.replace('.csv', '.db')
    
    print(f"Converting {csv_file} to SQLite database...")
    parse_csv_to_database(csv_file, db_file)
    print("\nExample queries:")
    print(f"  sqlite3 {db_file} 'SELECT * FROM functions LIMIT 10;'")
    print(f"  sqlite3 {db_file} 'SELECT * FROM functions ORDER BY total_time DESC LIMIT 20;'")
    print(f"  sqlite3 {db_file} 'SELECT COUNT(*) FROM functions WHERE indent_level = 0;'")


if __name__ == "__main__":
    main()
