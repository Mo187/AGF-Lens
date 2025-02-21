import os

# Use the PORT environment variable if set; otherwise, default to 5555
port = os.environ.get("PORT", "5555")
bind = f"0.0.0.0:{port}"
workers = 1
accesslog = '-'
loglevel = 'debug'
capture_output = True
enable_stdio_inheritance = True


