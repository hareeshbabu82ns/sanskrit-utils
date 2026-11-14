from ariadne import graphql_sync
from ariadne.explorer import ExplorerGraphiQL
from flask import Flask, request, jsonify
from flask_cors import CORS

from .database import dbConnection
from .schema import schema

app = Flask(__name__)
CORS(app)
explorer_html = ExplorerGraphiQL().html(None)


@app.route("/graphql", methods=["GET"])
def graphql_playground():
    return explorer_html, 200


@app.route("/graphql", methods=["POST"])
def graphql_server():
    data = request.get_json()
    context = {
        'request': request,
        'apiVersion': 'v1.0',
        'dbConnection': dbConnection,
    }
    success, result = graphql_sync(
        schema,
        data,
        context_value=context,
        debug=app.debug
    )
    return jsonify(result), 200 if success else 400
