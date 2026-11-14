"""Shared fixtures.

The suite needs no MongoDB and no network: the parser's lexicons ship inside
the sanskrit_parser package, and the Mongo client only connects on first use.
Importing the schema loads those lexicons, which takes a few seconds, so it
happens once per session.
"""
import pytest
from ariadne import graphql_sync


@pytest.fixture(scope='session')
def schema():
    from sanskrit_utils.schema import schema
    return schema


@pytest.fixture(scope='session')
def run(schema):
    """run(query, **variables) -> (data, [error messages])."""
    def run(query, **variables):
        _, result = graphql_sync(
            schema, {'query': query, 'variables': variables},
            context_value={'apiVersion': 'test'})
        return result.get('data'), [e['message'] for e in result.get('errors', [])]
    return run


@pytest.fixture(scope='session')
def gql(run):
    """gql(query, **variables) -> data; fails the test if the query errors."""
    def gql(query, **variables):
        data, errors = run(query, **variables)
        assert not errors, errors
        return data
    return gql


@pytest.fixture(scope='session')
def gql_error(run):
    """gql_error(query, **variables) -> the single error message expected."""
    def gql_error(query, **variables):
        _, errors = run(query, **variables)
        assert len(errors) == 1, errors
        return errors[0]
    return gql_error


@pytest.fixture(scope='session')
def service():
    from sanskrit_utils import parser_service
    return parser_service


@pytest.fixture(scope='session')
def client():
    from sanskrit_utils import app
    return app.test_client()
