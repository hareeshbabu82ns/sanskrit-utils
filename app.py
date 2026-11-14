#!/usr/bin/env python3
"""Entry point: `python app.py` (dev server) or `app:app` for uWSGI / `flask run`."""
import os

from sanskrit_utils import app

if __name__ == '__main__':
    app.run(
        debug=os.environ.get('FLASK_DEBUG', '1') == '1',
        host=os.environ.get('HOST', '127.0.0.1'),
        port=int(os.environ.get('PORT', '5000')),
    )
