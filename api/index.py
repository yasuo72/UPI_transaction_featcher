"""
Vercel Serverless Function Entrypoint for FinTrack UPI
Exposes the Flask WSGI application for serverless execution with guaranteed absolute paths.
"""

import sys
import os

# Guarantee root directory is in sys.path so app, core, templates, and static are found
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app

# Vercel WSGI entry point handler
app = app
