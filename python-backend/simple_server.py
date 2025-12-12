#!/usr/bin/env python3
"""
Ultra-simple HTTP server for datasheet finder (no Flask required).
Uses Python's built-in http.server module.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
from datasheet_finder import DatasheetFinder

# Initialize finder
finder = DatasheetFinder()


class DatasheetHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Serve the HTML page."""
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            with open('index.html', 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Handle search requests."""
        if self.path == '/search':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))

                component_name = data.get('component_name')
                manufacturer = data.get('manufacturer')
                num_results = data.get('num_results', 10)

                if not component_name:
                    self.send_error(400, 'component_name is required')
                    return

                # Perform search
                results = finder.search_datasheet(
                    component_name=component_name,
                    manufacturer=manufacturer,
                    num_results=num_results
                )

                # Send response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                response = json.dumps({
                    'results': results,
                    'count': len(results)
                })
                self.wfile.write(response.encode('utf-8'))

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = json.dumps({'error': str(e)})
                self.wfile.write(error_response.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging (optional)."""
        return


if __name__ == '__main__':
    port = 8081
    server = HTTPServer(('0.0.0.0', port), DatasheetHandler)
    print(f"Starting simple datasheet finder server...")
    print(f"Open http://localhost:{port} in your browser")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
