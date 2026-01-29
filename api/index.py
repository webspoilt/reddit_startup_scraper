import os
import sys

# Add the parent directory to sys.path so we can import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_ui import app

# Vercel needs the 'app' object to be exposed
# It handles the server execution
