#!/usr/bin/env python3
"""
Standalone web server for viewing VTune top-down profiling data from SQLite database.
Displays functions in a sortable table with drill-down capability.

Usage:
    python3 vtune_viewer.py [database_file] [port]
    
Example:
    python3 vtune_viewer.py step3-29834.21.top-down.db 8080
"""

import sqlite3
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
import html

# Default database file
DEFAULT_DB = "step3-29834.21.top-down.db"
DEFAULT_PORT = 8080

# Global variable for database path
DB_PATH = None


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
    return f"""<!DOCTYPE html>
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
        }}        .signature-cell {
            font-family: 'Courier New', monospace;
            font-size: 12px;
            word-break: break-word;
            overflow-wrap: break-word;
            max-width: 0;
            white-space: normal;
        }        .sort-controls {{
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
        .error {{
            color: #d13438;
            background-color: #fef0f0;
            padding: 15px;
            border-left: 4px solid #d13438;
            border-radius: 4px;
            margin: 20px 0;
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
    
    output = []
    output.append(html_header("VTune Profiling Data"))
    output.append(f"<h1>VTune Top-Down Profiling Data</h1>")
    output.append(f'<p class="info">Database: {html.escape(os.path.basename(DB_PATH))} | Total functions: {len(functions)} | Sorted by: {sort_title}</p>')
    
    # Sort controls
    output.append('<div class="sort-controls">')
    output.append('<strong>Sort by:</strong> ')
    
    params = {'sort': 'total'}
    active_class = ' active' if sort_by == 'total' else ''
    output.append(f'<a href="/?{urlencode(params)}" class="sort-button{active_class}">Total Time</a>')
    
    params['sort'] = 'self'
    active_class = ' active' if sort_by == 'self' else ''
    output.append(f'<a href="/?{urlencode(params)}" class="sort-button{active_class}">Self Time</a>')
    
    params['sort'] = 'name'
    active_class = ' active' if sort_by == 'name' else ''
    output.append(f'<a href="/?{urlencode(params)}" class="sort-button{active_class}">Function Name</a>')
    
    output.append('</div>')
    
    # Function table
    output.append('<table>')
    output.append('<thead>')
    output.append('<tr>')
    output.append('<th>Function</th>')
    output.append('<th class="time-cell">Total Time</th>')
    output.append('<th class="time-cell">Self Time</th>')
    output.append('<th class="percentage-cell">% of Total</th>')
    output.append('<th>Indent Level</th>')
    output.append('<th>Full Signature</th>')
    output.append('</tr>')
    output.append('</thead>')
    output.append('<tbody>')
    
    for func in functions:
        func_id, short_name, full_signature, total_time, self_time, percentage, indent_level = func
        
        params = {'view': 'function', 'id': func_id, 'sort': sort_by}
        link = f"/?{urlencode(params)}"
        
        output.append('<tr>')
        output.append(f'<td><a href="{html.escape(link)}" class="function-link">{html.escape(short_name)}</a></td>')
        output.append(f'<td class="time-cell">{format_time(total_time)}</td>')
        output.append(f'<td class="time-cell">{format_time(self_time)}</td>')
        output.append(f'<td class="percentage-cell">{percentage:.2f}%</td>')
        output.append(f'<td>{indent_level}</td>')
        output.append(f'<td class="signature-cell">{html.escape(full_signature)}</td>')
        output.append('</tr>')
    
    output.append('</tbody>')
    output.append('</table>')
    output.append(html_footer())
    
    return '\n'.join(output)


def show_function_details(conn, func_id, sort_by='total'):
    """Display function details and its immediate children."""
    cursor = conn.cursor()
    
    # Get function details
    cursor.execute('''
        SELECT id, short_name, full_signature, total_time, self_time, percentage, indent_level
        FROM functions
        WHERE id = ?
    ''', (func_id,))
    
    func = cursor.fetchone()
    
    output = []
    
    if not func:
        output.append(html_header("Function Not Found"))
        output.append("<h1>Function Not Found</h1>")
        output.append(f'<div class="error">Function ID "{html.escape(func_id)}" not found in database.</div>')
        params = {'sort': sort_by}
        output.append(f'<a href="/?{urlencode(params)}" class="back-link">← Back to Function List</a>')
        output.append(html_footer())
        return '\n'.join(output)
    
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
    
    output.append(html_header(f"Function Details: {short_name}"))
    
    # Back link
    params = {'sort': sort_by}
    output.append(f'<a href="/?{urlencode(params)}" class="back-link">← Back to Function List</a>')
    
    output.append(f"<h1>Function Details</h1>")
    
    # Function details
    output.append('<div class="function-details">')
    output.append(f'<h2>{html.escape(short_name)}</h2>')
    output.append(f'<p><strong>Total Time:</strong> {format_time(total_time)} ({percentage:.2f}% of total)</p>')
    output.append(f'<p><strong>Self Time:</strong> {format_time(self_time)}</p>')
    output.append(f'<p><strong>Indent Level:</strong> {indent_level}</p>')
    output.append(f'<p class="function-signature"><strong>Signature:</strong> {html.escape(full_signature)}</p>')
    output.append('</div>')
    
    # Children table
    if children:
        output.append(f'<h2>Immediate Children ({len(children)})</h2>')
        output.append('<table>')
        output.append('<thead>')
        output.append('<tr>')
        output.append('<th>Function</th>')
        output.append('<th class="time-cell">Total Time</th>')
        output.append('<th class="time-cell">Self Time</th>')
        output.append('<th class="percentage-cell">% of Total</th>')
        output.append('<th>Indent Level</th>')
        output.append('<th>Full Signature</th>')
        output.append('</tr>')
        output.append('</thead>')
        output.append('<tbody>')
        
        for child in children:
            child_id, child_short_name, child_full_signature, child_total_time, child_self_time, child_percentage, child_indent_level = child
            
            params = {'view': 'function', 'id': child_id, 'sort': sort_by}
            link = f"/?{urlencode(params)}"
            
            output.append('<tr>')
            output.append(f'<td><a href="{html.escape(link)}" class="function-link">{html.escape(child_short_name)}</a></td>')
            output.append(f'<td class="time-cell">{format_time(child_total_time)}</td>')
            output.append(f'<td class="time-cell">{format_time(child_self_time)}</td>')
            output.append(f'<td class="percentage-cell">{child_percentage:.2f}%</td>')
            output.append(f'<td>{child_indent_level}</td>')
            output.append(f'<td class="signature-cell">{html.escape(child_full_signature)}</td>')
            output.append('</tr>')
        
        output.append('</tbody>')
        output.append('</table>')
    else:
        output.append('<p class="info">This function has no children (leaf function).</p>')
    
    output.append(html_footer())
    
    return '\n'.join(output)


class VTuneRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for VTune viewer."""
    
    def do_GET(self):
        """Handle GET requests."""
        try:
            # Parse URL
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            # Extract parameters
            view = query_params.get('view', ['list'])[0]
            func_id = query_params.get('id', [''])[0]
            sort_by = query_params.get('sort', ['total'])[0]
            
            # Connect to database
            conn = sqlite3.connect(DB_PATH)
            
            # Generate response
            if view == 'function' and func_id:
                html_content = show_function_details(conn, func_id, sort_by)
            else:
                html_content = show_function_list(conn, sort_by)
            
            conn.close()
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            
        except Exception as e:
            # Error response
            error_html = html_header("Error")
            error_html += '<h1>Error</h1>'
            error_html += f'<div class="error"><pre>{html.escape(str(e))}</pre></div>'
            error_html += html_footer()
            
            self.send_response(500)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(error_html.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to customize log messages."""
        print(f"[{self.log_date_time_string()}] {format % args}")


def main():
    """Main entry point."""
    global DB_PATH
    
    # Parse command line arguments
    db_file = DEFAULT_DB
    port = DEFAULT_PORT
    
    if len(sys.argv) > 1:
        db_file = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            port = int(sys.argv[2])
        except ValueError:
            print(f"Invalid port number: {sys.argv[2]}")
            sys.exit(1)
    
    # Check if database exists
    if not os.path.exists(db_file):
        print(f"Error: Database file not found: {db_file}")
        print(f"\nUsage: {sys.argv[0]} [database_file] [port]")
        print(f"Example: {sys.argv[0]} step3-29834.21.top-down.db 8080")
        sys.exit(1)
    
    DB_PATH = os.path.abspath(db_file)
    
    # Start server
    server_address = ('', port)
    httpd = HTTPServer(server_address, VTuneRequestHandler)
    
    print(f"VTune Profiling Data Viewer")
    print(f"=" * 50)
    print(f"Database: {db_file}")
    print(f"Server running on: http://localhost:{port}")
    print(f"Press Ctrl+C to stop the server")
    print(f"=" * 50)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        httpd.shutdown()
        print("Server stopped.")


if __name__ == "__main__":
    main()
