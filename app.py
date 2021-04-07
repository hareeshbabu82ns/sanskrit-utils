#!/usr/bin/env python3

from sanskrit_utils import app

if __name__ == '__main__':
    app.run(
        debug=True,
        host=app.config['HOST'],
        port=app.config['PORT']
    )
