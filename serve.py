import http.server
import socketserver
import webbrowser
import os
from threading import Thread
import time
import socket
import sys

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def open_browser():
    """Open the browser after a short delay to ensure the server is running"""
    time.sleep(1.5)
    try:
        webbrowser.open('http://localhost:3000/login.html')
    except Exception as e:
        print(f"Could not open browser automatically: {e}")
        print("Please open http://localhost:3000/login.html manually in your browser")

def main():
    try:
        # Get the directory containing this file
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
        
        # Check if frontend directory exists
        if not os.path.exists(FRONTEND_DIR):
            print(f"Error: Frontend directory not found at {FRONTEND_DIR}")
            sys.exit(1)
        
        # Change to the frontend directory
        os.chdir(FRONTEND_DIR)
        
        # Create the server
        PORT = 3000
        if is_port_in_use(PORT):
            print(f"Error: Port {PORT} is already in use")
            print("Please close any applications using this port or try a different port")
            sys.exit(1)
            
        Handler = CORSRequestHandler
        
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Serving frontend at http://localhost:{PORT}")
            print("Available pages:")
            print("- Login: http://localhost:3000/login.html")
            print("- Register: http://localhost:3000/register.html")
            print("- Student Dashboard: http://localhost:3000/student_dashboard.html")
            print("- Lecturer Dashboard: http://localhost:3000/lecturer_dashboard.html")
            print("\nPress Ctrl+C to stop the server")
            
            # Open the browser in a separate thread
            Thread(target=open_browser, daemon=True).start()
            
            # Start the server
            httpd.serve_forever()
    except OSError as e:
        print(f"Error: Could not start server on port {PORT}. Port might be in use.")
        print("Try using a different port or closing any applications that might be using this port.")
        print(f"Error details: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 