import sys

from sanskrit_utils.database import db_session
from flask import Flask
from flask_graphql import GraphQLView
from sanskrit_utils.schema import schema

app = Flask(__name__)
app.debug = True
app.config['HOST'] = '127.0.0.1'
app.config['PORT'] = 5000


app.add_url_rule(
    '/graphql',
    view_func=GraphQLView.as_view(
        'graphql',
        schema=schema,
        graphiql=True,
        context={'session': db_session}
    )
)
