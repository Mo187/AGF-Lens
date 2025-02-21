import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
workers = 1
accesslog = '-'
loglevel = 'debug'
capture_output = True
enable_stdio_inheritance = True


