#!/usr/bin/env python3
"""
Simple HTTP server to serve the AlphaVelocity frontend
"""
import http.server
import socketserver
import os
import sys

# Change to frontend directory
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend')
os.chdir(frontend_dir)

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def run_frontend_server(port=3000):
    """Run the frontend HTTP server"""
    handler = CustomHTTPRequestHandler

    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"🌐 AlphaVelocity Frontend Server starting on http://localhost:{port}")
        print(f"📁 Serving files from: {os.getcwd()}")
        print(f"🚀 Open http://localhost:{port} in your browser")
        print(f"\n⚡ Frontend ready! Press Ctrl+C to stop.")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print(f"\n🛑 Frontend server stopped.")

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    run_frontend_server(port)