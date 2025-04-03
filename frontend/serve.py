import http.server
import socketserver
import webbrowser
import os
from threading import Thread
import time

def open_browser():
    """Open the browser after a short delay to ensure the server is running"""
    time.sleep(1.5)
    webbrowser.open('http://localhost:3000/login.html')

def main():
    # Get the directory containing this file
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the frontend directory
    os.chdir(BASE_DIR)
    
    # Create the server
    PORT = 3000
    Handler = http.server.SimpleHTTPRequestHandler
    
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
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()

if __name__ == "__main__":
    main() 