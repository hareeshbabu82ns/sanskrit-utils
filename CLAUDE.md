# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Flask + Ariadne **GraphQL API** for Sanskrit: transliteration between scripts (`indic_transliteration`), sandhi split/join/tagging/parsing (`sanskrit-parser`), and search/CRUD over ~900k dictionary entries stored in **MongoDB**. Single endpoint: `GET /graphql` serves the GraphiQL explorer, `POST /graphql` executes queries. Example queries are in README.md under "API".

## Commands

```sh
./run.sh               # create .venv if missing, pip install when requirements.txt changes, load .env, run app.py
./run.sh --install     # env setup only
PORT=5055 FLASK_DEBUG=0 ./run.sh

# smoke test a running server (no MongoDB needed for these)
curl -s localhost:5000/graphql -H 'Content-Type: application/json' \
  -d '{"query":"{ transliterate(text: \"harIS\", schemeFrom: SLP1, schemeTo: DEVANAGARI) }"}'

python -m compileall -q app.py sanskrit_utils scripts   # what CI runs; there is no test suite or linter config

scripts/release.py patch|minor|major [--dry-run] [--yes]   # tag vX.Y.Z and push -> CI builds image + GitHub Release
```

Config is via env vars (see `.env.example`): `MONGO_DB_HOST/PORT/DB/USER/PASSWORD`, `HOST`, `PORT`, `FLASK_DEBUG`. With an empty `MONGO_DB_PASSWORD` the client connects without auth. The Mongo client is lazy (`connect=False`), so the server starts and parser/transliteration queries work with no DB; only dictionary queries need MongoDB.

Startup is slow (several seconds): `sans_parser.py` builds a `sanskrit_parser.Parser` and `LexicalSandhiAnalyzer` at import time. In debug mode the reloader does this twice.

## Architecture

- `app.py` → imports `sanskrit_utils.app` (Flask). Also the uWSGI module (`app:app`) in Docker.
- `sanskrit_utils/schema/` — schema-first Ariadne. All `*.graphql` files in this directory are loaded and merged (`schema.graphql` defines base `Query`/`Mutation`; others use `extend type`). Resolvers are Python modules that import the shared `query`/`mutation` ObjectTypes from `sanskrit_utils.schema` and register with `@query.field(...)`.
  - **Import order in `schema/__init__.py` matters**: `Query`/`Mutation` must be imported before `Sanscript`/`sans_parser`, which import them back from the package (circular by design). A new resolver module must be imported there, and any new ObjectType/EnumType bindables added to `type_resolvers`.
  - `Sanscript.py` — `SanscriptScheme` and `Dictionaries` Python enums bound to GraphQL enums (resolvers receive enum members; use `.value`). Holds transliteration plus dictionary search/browse/CRUD resolvers. Resolvers inspect `info.field_nodes` to fetch or compute only the requested fields.
  - `sans_parser.py` — splits/joins/tags/presegmented/parse resolvers. They mutate the module-global `parser`'s encoding settings per request, so they are not thread-safe.
- `sanskrit_utils/database.py` — env-configured pymongo client. The API reads collections `dictEntries` and `dictPhonetics`.
- `sanskrit_utils/loaders/` — standalone one-off ETL scripts, not imported by the API. Run them from the **repo root** as `python sanskrit_utils/loaders/<X>.py`: they read source SQLite dictionaries from `tmp/<dict>.sqlite` (gitignored, local only) and use sibling imports (`from utils import ...`).
  - `LexiconDicToMongodb.py`, `SanDicDhatuPataToMongodb.py`, `SetupMongoDb.py` (indexes), `ParseDictEntries.py` (builds `dictPhonetics`) target the API's `dictEntries`.
  - `DevHub*` loaders write a **different** collection, `DictWords`, in a different document shape, for a separate "devhub" app. Per README, `DevHubLexiconDicToMongodb.py` is the one that supports all current dictionaries.
- Dictionary documents: `word`/`desc` are dicts keyed by scheme (`slp1`, `devanagari`, …), plus `wordOriginal`, `descOriginal`, `origin` (a `Dictionaries` value), and `wordIndex`. Search runs on `word.slp1`/`desc.slp1` (text index + regex); input is transliterated to SLP1 first.

## Deployment

- `Dockerfile` (prod): nginx (`docker/nginx.conf`, :80) → uWSGI unix socket (`docker/uwsgi.ini`), launched by `docker/start.sh`. `Dockerfile.dev` runs `app.py` on :5000.
- `.github/workflows/docker-publish.yml` pushes to `ghcr.io/<repo>`. Tags `vX.Y.Z` produce image tags `X.Y.Z`, `X.Y`, `X` (if X>0) and `latest`, plus a GitHub Release. Branch pushes produce `master`/`sha-*` images. PRs only build.
- Legacy pipeline that still exists: `.drone.yml` builds to a private registry and runs `.ansible/playbook.yml` (k8s deployment template, vault-encrypted vars).
