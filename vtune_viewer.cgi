#!/usr/bin/env python3
"""
CGI script for viewing VTune top-down profiling data from SQLite database.
Displays functions in a sortable table with drill-down capability.
"""

import cgi
import cgitb
import sqlite3
import os
import sys
from urllib.parse import urlencode
import html

# Enable CGI error reporting
cgitb.enable()

# Default database file - adjust this path as needed
DEFAULT_DB = "step3-29834.21.top-down.db"

def get_db_path():
    """Get the database path from query string or use default."""
    form = cgi.FieldStorage()
    db_file = form.getfirst('db', DEFAULT_DB)
    
    # Security: ensure the db file is in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, os.path.basename(db_file))
    
    if not os.path.exists(db_path):
        return None
    return db_path


def format_time(seconds):
    """Format time in seconds to human-readable string."""
    if seconds >= 1.0:
        return f"{seconds:.3f}s"
    elif seconds >= 0.001:
        return f"{seconds * 1000:.3f}ms"
    elif seconds >= 0.000001:
        return f"{seconds * 1000000:.3f}µs"
    else:
        return f"{seconds * 1000000000:.3f}ns"


def html_header(title):
    """Generate HTML header."""
    return f"""Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{html.escape(title)}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #0078d4;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #0078d4;
            color: white;
            cursor: pointer;
            user-select: none;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        th:hover {{
            background-color: #005a9e;
        }}
        th.sortable::after {{
            content: " ⇅";
            opacity: 0.5;
        }}
        th.sorted-asc::after {{
            content: " ↑";
            opacity: 1;
        }}
        th.sorted-desc::after {{
            content: " ↓";
            opacity: 1;
        }}
        tr:hover {{
            background-color: #f0f0f0;
        }}
        .function-link {{
            color: #0078d4;
            text-decoration: none;
            cursor: pointer;
        }}
        .function-link:hover {{
            text-decoration: underline;
            color: #005a9e;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            padding: 8px 16px;
            background-color: #0078d4;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }}
        .back-link:hover {{
            background-color: #005a9e;
        }}
        .function-details {{
            background-color: #f9f9f9;
            padding: 15px;
            border-left: 4px solid #0078d4;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .function-signature {{
            font-family: 'Courier New', monospace;
            font-size: 14px;
            word-break: break-all;
        }}
        .time-cell {{
            text-align: right;
            font-family: 'Courier New', monospace;
        }}
        .percentage-cell {{
            text-align: right;
        }}
        .signature-cell {{
            font-family: 'Courier New', monospace;
            font-size: 12px;
            word-break: break-word;
            overflow-wrap: break-word;
            max-width: 0;
            white-space: normal;
        }}
        .sort-controls {{
            margin: 20px 0;
            padding: 10px;
            background-color: #f0f0f0;
            border-radius: 4px;
        }}
        .sort-button {{
            padding: 6px 12px;
            margin-right: 10px;
            background-color: #0078d4;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            border: none;
            cursor: pointer;
        }}
        .sort-button:hover {{
            background-color: #005a9e;
        }}
        .sort-button.active {{
            background-color: #005a9e;
            font-weight: bold;
        }}
        .info {{
            color: #666;
            font-size: 14px;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
<div class="container">
"""


def html_footer():
    """Generate HTML footer."""
    return """
</div>
</body>
</html>
"""


def show_function_list(conn, sort_by='total'):
    """Display list of all functions with sorting."""
    form = cgi.FieldStorage()
    db_file = form.getfirst('db', DEFAULT_DB)
    
    # Determine sort order
    order_by = "total_time DESC"
    sort_title = "Total Time"
    
    if sort_by == 'self':
        order_by = "self_time DESC"
        sort_title = "Self Time"
    elif sort_by == 'name':
        order_by = "short_name ASC"
        sort_title = "Function Name"
    
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT id, short_name, full_signature, total_time, self_time, percentage, indent_level
        FROM functions
        ORDER BY {order_by}
    ''')
    
    functions = cursor.fetchall()
    
    print(html_header("VTune Profiling Data"))
    print(f"<h1>VTune Top-Down Profiling Data</h1>")
    print(f'<p class="info">Database: {html.escape(db_file)} | Total functions: {len(functions)} | Sorted by: {sort_title}</p>')
    
    # Sort controls
    print('<div class="sort-controls">')
    print('<strong>Sort by:</strong> ')
    
    params = {'db': db_file, 'sort': 'total'}
    active_class = ' active' if sort_by == 'total' else ''
    print(f'<a href="?{urlencode(params)}" class="sort-button{active_class}">Total Time</a>')
    
    params['sort'] = 'self'
    active_class = ' active' if sort_by == 'self' else ''
    print(f'<a href="?{urlencode(params)}" class="sort-button{active_class}">Self Time</a>')
    
    params['sort'] = 'name'
    active_class = ' active' if sort_by == 'name' else ''
    print(f'<a href="?{urlencode(params)}" class="sort-button{active_class}">Function Name</a>')
    
    print('</div>')
    
    # Function table
    print('<table>')
    print('<thead>')
    print('<tr>')
    print('<th>Function</th>')
    print('<th class="time-cell">Total Time</th>')
    print('<th class="time-cell">Self Time</th>')
    print('<th class="percentage-cell">% of Total</th>')
    print('<th>Indent Level</th>')
    print('<th>Full Signature</th>')
    print('</tr>')
    print('</thead>')
    print('<tbody>')
    
    for func in functions:
        func_id, short_name, full_signature, total_time, self_time, percentage, indent_level = func
        
        params = {'db': db_file, 'view': 'function', 'id': func_id, 'sort': sort_by}
        link = f"?{urlencode(params)}"
        
        print('<tr>')
        print(f'<td><a href="{html.escape(link)}" class="function-link">{html.escape(short_name)}</a></td>')
        print(f'<td class="time-cell">{format_time(total_time)}</td>')
        print(f'<td class="time-cell">{format_time(self_time)}</td>')
        print(f'<td class="percentage-cell">{percentage:.2f}%</td>')
        print(f'<td>{indent_level}</td>')
        print(f'<td class="signature-cell">{html.escape(full_signature)}</td>')
        print('</tr>')
    
    print('</tbody>')
    print('</table>')
    print(html_footer())


def show_function_details(conn, func_id, sort_by='total'):
    """Display function details and its immediate children."""
    form = cgi.FieldStorage()
    db_file = form.getfirst('db', DEFAULT_DB)
    
    cursor = conn.cursor()
    
    # Get function details
    cursor.execute('''
        SELECT id, short_name, full_signature, total_time, self_time, percentage, indent_level
        FROM functions
        WHERE id = ?
    ''', (func_id,))
    
    func = cursor.fetchone()
    if not func:
        print(html_header("Function Not Found"))
        print("<h1>Function Not Found</h1>")
        print(f'<p>Function ID "{html.escape(func_id)}" not found in database.</p>')
        params = {'db': db_file, 'sort': sort_by}
        print(f'<a href="?{urlencode(params)}" class="back-link">← Back to Function List</a>')
        print(html_footer())
        return
    
    func_id, short_name, full_signature, total_time, self_time, percentage, indent_level = func
    
    # Get children - use cache table for faster lookups
    cursor.execute('''
        SELECT child_id, child_short_name, child_full_signature, 
               child_total_time, child_self_time, child_percentage, child_indent_level
        FROM function_children_cache
        WHERE parent_id = ?
        ORDER BY child_total_time DESC
    ''', (func_id,))
    
    children = cursor.fetchall()
    
    print(html_header(f"Function Details: {short_name}"))
    
    # Back link
    params = {'db': db_file, 'sort': sort_by}
    print(f'<a href="?{urlencode(params)}" class="back-link">← Back to Function List</a>')
    
    print(f"<h1>Function Details</h1>")
    
    # Function details
    print('<div class="function-details">')
    print(f'<h2>{html.escape(short_name)}</h2>')
    print(f'<p><strong>Total Time:</strong> {format_time(total_time)} ({percentage:.2f}% of total)</p>')
    print(f'<p><strong>Self Time:</strong> {format_time(self_time)}</p>')
    print(f'<p><strong>Indent Level:</strong> {indent_level}</p>')
    print(f'<p class="function-signature"><strong>Signature:</strong> {html.escape(full_signature)}</p>')
    print('</div>')
    
    # Children table
    if children:
        print(f'<h2>Immediate Children ({len(children)})</h2>')
        print('<table>')
        print('<thead>')
        print('<tr>')
        print('<th>Function</th>')
        print('<th class="time-cell">Total Time</th>')
        print('<th class="time-cell">Self Time</th>')
        print('<th class="percentage-cell">% of Total</th>')
        print('<th>Indent Level</th>')
        print('<th>Full Signature</th>')
        print('</tr>')
        print('</thead>')
        print('<tbody>')
        
        for child in children:
            child_id, child_short_name, child_full_signature, child_total_time, child_self_time, child_percentage, child_indent_level = child
            
            params = {'db': db_file, 'view': 'function', 'id': child_id, 'sort': sort_by}
            link = f"?{urlencode(params)}"
            
            print('<tr>')
            print(f'<td><a href="{html.escape(link)}" class="function-link">{html.escape(child_short_name)}</a></td>')
            print(f'<td class="time-cell">{format_time(child_total_time)}</td>')
            print(f'<td class="time-cell">{format_time(child_self_time)}</td>')
            print(f'<td class="percentage-cell">{child_percentage:.2f}%</td>')
            print(f'<td>{child_indent_level}</td>')
            print(f'<td class="signature-cell">{html.escape(child_full_signature)}</td>')
            print('</tr>')
        
        print('</tbody>')
        print('</table>')
    else:
        print('<p class="info">This function has no children (leaf function).</p>')
    
    print(html_footer())


def main():
    """Main CGI handler."""
    try:
        # Get database path
        db_path = get_db_path()
        
        if not db_path:
            print(html_header("Database Not Found"))
            print("<h1>Error: Database Not Found</h1>")
            print(f"<p>Could not find database file: {html.escape(DEFAULT_DB)}</p>")
            print("<p>Please ensure the database file is in the same directory as this CGI script.</p>")
            print(html_footer())
            return
        
        # Parse query parameters
        form = cgi.FieldStorage()
        view = form.getfirst('view', 'list')
        func_id = form.getfirst('id', '')
        sort_by = form.getfirst('sort', 'total')
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        
        # Route to appropriate view
        if view == 'function' and func_id:
            show_function_details(conn, func_id, sort_by)
        else:
            show_function_list(conn, sort_by)
        
        conn.close()
        
    except Exception as e:
        print(html_header("Error"))
        print("<h1>Error</h1>")
        print(f"<pre>{html.escape(str(e))}</pre>")
        print(html_footer())
        import traceback
        print(f"<pre>{html.escape(traceback.format_exc())}</pre>")


if __name__ == "__main__":
    main()
