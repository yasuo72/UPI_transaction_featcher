"""
Vercel Serverless Function Entrypoint for FinTrack UPI
Exposes the Flask WSGI application for serverless execution.
"""

from app import app

# Vercel WSGI entry point handler
app = app
