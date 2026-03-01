import sys
import os

# Ensure root of repo is on the path so 'app', 'models', 'services' etc. are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: F401  — Vercel picks up the 'app' WSGI object from here
