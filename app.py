#!/usr/bin/env python3

from sanskrit_utils import app
from sanskrit_utils.database import db_session, init_db


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')


if __name__ == '__main__':
    init_db()
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT']
    )
