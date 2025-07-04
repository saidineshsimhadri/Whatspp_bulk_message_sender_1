from flask import Flask, render_template, request, jsonify
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import webbrowser
from threading import Timer
import urllib.parse
import os
import platform
import socket
import sys
import random
import subprocess

# Create a simple Flask app
app = Flask(__name__)

# Print startup message
print("="*50)
print("WhatsApp Bulk Sender - Starting up")
print("="*50)
print(f"Python version: {sys.version}")
print(f"Operating system: {platform.system()} {platform.release()}")
print("="*50)

def check_port_in_use(port):
    """Check if the specified port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_chrome_path():
    """Find Chrome executable path based on OS."""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        chrome_paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chromium.app/Contents/MacOS/Chromium',
            '~/Applications/Chromium.app/Contents/MacOS/Chromium'
        ]
        
        for path in chrome_paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                print(f"Found Chrome at: {expanded_path}")
                return expanded_path
                
        try:
            mdfind_output = subprocess.check_output(
                ['mdfind', 'kMDItemCFBundleIdentifier == "com.google.Chrome"'], 
                text=True
            ).strip()
            
            if mdfind_output:
                chrome_app_path = mdfind_output.split('\n')[0]
                chrome_bin_path = os.path.join(chrome_app_path, 'Contents/MacOS/Google Chrome')
                if os.path.exists(chrome_bin_path):
                    print(f"Found Chrome using mdfind at: {chrome_bin_path}")
                    return chrome_bin_path
        except Exception as e:
            print(f"Error using mdfind: {e}")
            
    elif system == "Windows":
        chrome_paths = [
            os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Google\\Chrome\\Application\\chrome.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'Google\\Chrome\\Application\\chrome.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google\\Chrome\\Application\\chrome.exe')
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                print(f"Found Chrome at: {path}")
                return path
                
    else:  # Linux
        chrome_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser'
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                print(f"Found Chrome at: {path}")
                return path
                
        try:
            which_output = subprocess.check_output(['which', 'google-chrome'], text=True).strip()
            if which_output and os.path.exists(which_output):
                print(f"Found Chrome using which at: {which_output}")
                return which_output
        except Exception:
            pass
            
    print("Chrome executable not found in common locations")
    return None

def init_driver():
    """Initialize WebDriver with Chrome first, then Firefox as fallback."""
    # Try Chrome first
    try:
        print("Attempting to initialize Chrome WebDriver...")
        
        chrome_path = find_chrome_path()
        if chrome_path:
            print(f"Using Chrome at: {chrome_path}")
            
            chrome_options = ChromeOptions()
            chrome_options.binary_location = chrome_path
            
            # --- MODIFICATION START: Add options for stability and background operation ---
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--start-maximized")
            
            # These flags help the browser run smoothly even when the window is not in focus
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            # --- MODIFICATION END ---
            
            try:
                try:
                    from webdriver_manager.chrome import ChromeDriverManager
                    driver = webdriver.Chrome(
                        service=ChromeService(ChromeDriverManager().install()),
                        options=chrome_options
                    )
                    print("Chrome driver initialized successfully with webdriver-manager!")
                    return driver
                except ImportError:
                    driver = webdriver.Chrome(options=chrome_options)
                    print("Chrome driver initialized successfully with default method!")
                    return driver
            except Exception as chrome_error:
                print(f"Error initializing Chrome driver: {str(chrome_error)}")
                print("Falling back to Firefox...")
        else:
            print("Chrome not found. Falling back to Firefox...")
    except Exception as e:
        print(f"Error setting up Chrome options: {str(e)}")
        print("Falling back to Firefox...")
    
    # Firefox fallback (Note: Background stability options are more effective on Chrome)
    try:
        print("Attempting to initialize Firefox WebDriver...")
        firefox_options = FirefoxOptions()
        firefox_options.set_preference("dom.webnotifications.enabled", False)
        
        try:
            from webdriver_manager.firefox import GeckoDriverManager
            driver = webdriver.Firefox(
                service=FirefoxService(GeckoDriverManager().install()),
                options=firefox_options
            )
            print("Firefox driver initialized successfully with webdriver-manager!")
            return driver
        except Exception as firefox_manager_error:
            print(f"Firefox initialization with webdriver-manager failed: {str(firefox_manager_error)}")
            try:
                driver = webdriver.Firefox(options=firefox_options)
                print("Firefox driver initialized successfully with default method!")
                return driver
            except Exception as firefox_direct_error:
                print(f"Firefox direct initialization failed: {str(firefox_direct_error)}")
        
        print("\nTroubleshooting steps:")
        print("1. Make sure either Chrome or Firefox is installed on your system")
        print("2. Try running 'pip install --upgrade webdriver-manager selenium'")
        
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"Error in Firefox fallback: {str(e)}")
        return None

def send_whatsapp_message(driver, phone, message):
    """Send a WhatsApp message to a specific phone number."""
    try:
        encoded_message = urllib.parse.quote(message)
        url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_message}"
        print(f"Navigating to: {url}")
        driver.get(url)
        
        print(f"Waiting for chat to load for {phone}...")
        
        # Check for QR code only on the first attempt
        try:
            qr_code_xpath = '//div[@data-ref and contains(@aria-label, "QR code")]'
            WebDriverWait(driver, 7).until(EC.presence_of_element_located((By.XPATH, qr_code_xpath)))
            print("QR code detected. Please scan it with your phone to log in to WhatsApp Web.")
            print("Waiting up to 60 seconds for you to scan the QR code...")
            # Wait for the chat input field to appear after QR code is scanned
            WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]')))
        except Exception:
            # Already logged in or QR code not found, continue
            pass
        
        # Wait for the main chat input field to be ready
        chat_input_xpath = '//div[@contenteditable="true"][@data-tab="10"]'
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, chat_input_xpath)))
        
        time.sleep(random.uniform(0.5, 1.5)) # Short delay for stability
        
        print(f"Looking for send button for {phone}...")
        send_button_xpath = '//button[@aria-label="Send"] | //span[@data-icon="send"]'
        send_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, send_button_xpath)))
        
        # --- MODIFICATION START: Robust click method ---
        # Try standard click first, if it fails (e.g., in a background tab), use JavaScript click
        try:
            send_button.click()
            print(f"Clicked send button for {phone} using standard method.")
        except Exception as e:
            print(f"Standard click failed: {e}. Trying JavaScript click.")
            driver.execute_script("arguments[0].click();", send_button)
            print(f"Clicked send button for {phone} using JavaScript fallback.")
        # --- MODIFICATION END ---
        
        time.sleep(random.uniform(1.0, 2.0)) # Shorter delay after sending
        print(f"Message sent successfully to {phone}")
        return True
        
    except Exception as e:
        print(f"Error sending to {phone}: {str(e)}")
        try:
            screenshot_path = f"error_screenshot_{phone}_exception.png"
            driver.save_screenshot(screenshot_path)
            print(f"Screenshot saved to {screenshot_path}")
        except:
            pass
        return False

def create_templates_directory():
    """Create the templates directory if it doesn't exist."""
    if not os.path.exists('templates'):
        print("Creating templates directory...")
        os.makedirs('templates')
        return True
    return False

def create_index_html():
    """Create the index.html file if it doesn't exist."""
    if not os.path.exists('templates/index.html'):
        print("Creating index.html file...")
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WhatsApp Bulk Sender</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            padding: 20px;
            background-color: #f8f9fa;
        }
        .container {
            max-width: 800px;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .results {
            margin-top: 20px;
            display: none;
        }
        .progress-container {
            margin-top: 20px;
            display: none;
        }
        #csvInfo {
            margin-top: 15px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>WhatsApp Bulk Message Sender</h1>
            <p class="text-muted">Upload a CSV file with mobile numbers and messages to send</p>
        </div>
        
        <form id="uploadForm" enctype="multipart/form-data">
            <div class="mb-3">
                <label for="csvFile" class="form-label">CSV File (must contain 'Mobile' and 'Message' columns)</label>
                <input type="file" class="form-control" id="csvFile" name="file" accept=".csv" required>
                <div id="csvInfo" class="alert alert-info mt-2">
                    <p><strong>CSV Preview:</strong> <span id="csvPreview"></span></p>
                </div>
            </div>
            
            <div class="d-grid gap-2">
                <button type="submit" class="btn btn-primary" id="sendButton">Send Messages</button>
            </div>
        </form>
        
        <div class="progress-container">
            <label>Sending messages...</label>
            <div class="progress">
                <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%"></div>
            </div>
            <p class="mt-2">Please wait and don't close this window. If prompted, scan the WhatsApp QR code with your phone.</p>
        </div>
        
        <div class="results">
            <h3>Results</h3>
            <div class="alert alert-info">
                <p>Please keep this window open until all messages are sent.</p>
                <p>You'll need to scan the WhatsApp QR code when prompted.</p>
            </div>
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Phone</th>
                        <th>Status</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody id="resultsTable">
                </tbody>
            </table>
            <div class="alert alert-success" id="completionMessage" style="display: none;">
                All messages have been processed!
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.getElementById('uploadForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('csvFile');
            if (!fileInput.files.length) {
                alert('Please select a CSV file');
                return;
            }
            
            const file = fileInput.files[0];
            if (!file.name.endsWith('.csv')) {
                alert('Please select a CSV file');
                return;
            }
            
            // Show progress
            document.querySelector('.progress-container').style.display = 'block';
            document.getElementById('sendButton').disabled = true;
            
            const formData = new FormData();
            formData.append('file', file);
            
            fetch('/send', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert('Error: ' + data.error);
                    document.getElementById('sendButton').disabled = false;
                } else {
                    displayResults(data.results);
                }
                document.querySelector('.progress-container').style.display = 'none';
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
                document.getElementById('sendButton').disabled = false;
                document.querySelector('.progress-container').style.display = 'none';
            });
        });
        
        function displayResults(results) {
            const resultsTable = document.getElementById('resultsTable');
            resultsTable.innerHTML = '';
            
            results.forEach(result => {
                const row = document.createElement('tr');
                
                const phoneCell = document.createElement('td');
                phoneCell.textContent = result.phone;
                
                const statusCell = document.createElement('td');
                statusCell.textContent = result.status;
                if (result.status === 'Success') {
                    statusCell.classList.add('text-success');
                } else {
                    statusCell.classList.add('text-danger');
                }
                
                const detailsCell = document.createElement('td');
                detailsCell.textContent = result.reason || '-';
                
                row.appendChild(phoneCell);
                row.appendChild(statusCell);
                row.appendChild(detailsCell);
                
                resultsTable.appendChild(row);
            });
            
            document.querySelector('.results').style.display = 'block';
            document.getElementById('completionMessage').style.display = 'block';
        }
        
        // Preview CSV file
        document.getElementById('csvFile').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file && file.name.endsWith('.csv')) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const content = e.target.result;
                    const lines = content.split('\\n');
                    if (lines.length > 0) {
                        const headers = lines[0].trim();
                        const preview = `Headers: ${headers}`;
                        document.getElementById('csvPreview').textContent = preview;
                        document.getElementById('csvInfo').style.display = 'block';
                    }
                };
                reader.readAsText(file);
            }
        });
    </script>
</body>
</html>
"""
        with open('templates/index.html', 'w') as f:
            f.write(html_content)
        return True
    return False

def create_sample_csv():
    """Create a sample CSV file if it doesn't exist."""
    if not os.path.exists('sample_messages.csv'):
        print("Creating sample CSV file...")
        csv_content = """Mobile,Message
919876543210,Hello! This is a test message from the WhatsApp Bulk Sender.
918765432109,Hi there! How are you doing today?"""
        with open('sample_messages.csv', 'w') as f:
            f.write(csv_content)
        return True
    return False

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/test')
def test():
    return jsonify({"status": "ok", "message": "Server is running"})

@app.route('/send', methods=['POST'])
def handle_send():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Only CSV files allowed'}), 400
    
    try:
        temp_file_path = f'temp_upload_{random.randint(1000, 9999)}.csv'
        file.save(temp_file_path)
        
        df = pd.read_csv(temp_file_path)
        
        if 'Mobile' not in df.columns or 'Message' not in df.columns:
            os.remove(temp_file_path)
            return jsonify({'error': 'CSV must contain "Mobile" and "Message" columns'}), 400
        
        driver = init_driver()
        if driver is None:
            os.remove(temp_file_path)
            return jsonify({'error': 'Failed to initialize browser driver. Please make sure Chrome is installed.'}), 500
        
        results = []
        total_messages = len(df)
        
        for index, row in df.iterrows():
            phone = str(row['Mobile']).strip()
            msg = str(row['Message']).strip()
            
            if not phone or len(phone) < 10:
                results.append({'phone': phone, 'status': 'Failed', 'reason': 'Invalid phone number'})
                continue
            
            if send_whatsapp_message(driver, phone, msg):
                results.append({'phone': phone, 'status': 'Success'})
            else:
                results.append({'phone': phone, 'status': 'Failed', 'reason': 'Message sending failed'})
            
            progress = ((index + 1) / total_messages) * 100
            print(f"Progress: {progress:.1f}% ({index + 1}/{total_messages})")
            
            # --- MODIFICATION START: Reduced delay for faster sending ---
            # Shorter, random delay to appear more human-like but still be fast.
            # WARNING: Making this too short (e.g., less than 1-2 seconds)
            # significantly increases the risk of your number being blocked by WhatsApp.
            delay = random.uniform(2.0, 4.0) 
            print(f"Waiting {delay:.1f} seconds before sending next message...")
            time.sleep(delay)
            # --- MODIFICATION END ---
        
        driver.quit()
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return jsonify({'results': results})
    
    except Exception as e:
        print(f"Error in handle_send: {str(e)}")
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if 'driver' in locals() and driver:
            driver.quit()
        return jsonify({'error': str(e)}), 500

def open_browser(port):
    """Open the browser with multiple fallback methods."""
    url = f"http://localhost:{port}"
    print(f"Attempting to open browser at {url}")
    try:
        webbrowser.open_new(url)
        print("Browser opened using webbrowser.open_new()")
    except Exception as e:
        print(f"Failed to open browser with webbrowser.open_new(): {e}")
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.run(['open', url], check=True)
                print("Browser opened using 'open' command")
            elif system == "Windows":
                subprocess.run(['start', url], shell=True, check=True)
                print("Browser opened using 'start' command")
            elif system == "Linux":
                subprocess.run(['xdg-open', url], check=True)
                print("Browser opened using 'xdg-open' command")
        except Exception as e2:
            print(f"Failed to open browser with system command: {e2}")
            print(f"Please manually open {url} in your browser")

# --- MODIFICATION START: This block is updated to prevent opening two browsers ---
if __name__ == '__main__':
    print("Starting WhatsApp Bulk Sender application....")
    
    create_templates_directory()
    create_index_html()
    create_sample_csv()
    
    # Find an available port for the server
    ports_to_try = [9090, 9091, 9092, 8080, 8081, 8082, 5000]
    port = None
    for p in ports_to_try:
        if not check_port_in_use(p):
            port = p
            break
    
    if port is None:
        port = 5000 # Fallback if all common ports are in use
    
    print(f"Server will run on port {port}")
    
    # This check prevents the browser from opening twice when debug=True.
    # The code inside this `if` block will only run in the main process,
    # not in the reloader's child process.
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        Timer(2, open_browser, args=[port]).start()
    
    print(f"Starting Flask app on http://127.0.0.1:{port}")
    try:
        # debug=True automatically enables the reloader. The check above handles it.
        app.run(debug=True, port=port, host='127.0.0.1')
    except OSError as e:
        print(f"Error starting Flask server: {e}")
# --- MODIFICATION END --