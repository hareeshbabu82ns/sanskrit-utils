# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Flask + Ariadne **GraphQL API** for Sanskrit: transliteration between scripts (`indic_transliteration`), sandhi split/join, morphological tags, sentence analysis, dhatupatha and pratyahara lookup (`sanskrit-parser`), metre (`sanskrit-util`), and search/CRUD over ~900k dictionary entries stored in **MongoDB**. Single endpoint: `GET /graphql` serves the GraphiQL explorer, `POST /graphql` executes queries. Example queries are in README.md under "API".

## Commands

```sh
./run.sh               # create .venv if missing, pip install when requirements.txt changes, load .env, run app.py
./run.sh --install     # env setup only
PORT=5055 FLASK_DEBUG=0 ./run.sh

# smoke test a running server (no MongoDB needed for these)
curl -s localhost:5000/graphql -H 'Content-Type: application/json' \
  -d '{"query":"{ transliterate(text: \"harIS\", schemeFrom: SLP1, schemeTo: DEVANAGARI) }"}'

.venv/bin/pip install -r requirements-dev.txt           # adds pytest
.venv/bin/python -m pytest                              # whole suite, ~7s, no MongoDB or network
.venv/bin/python -m pytest tests/test_api_parse.py -k conll   # one file / one test
python -m compileall -q app.py sanskrit_utils scripts   # CI's `check` job; CI's `test` job runs pytest. No linter config

scripts/release.py patch|minor|major [--dry-run] [--yes]   # tag vX.Y.Z and push -> CI builds image + GitHub Release
```

Config is via env vars (see `.env.example`): `MONGO_DB_HOST/PORT/DB/USER/PASSWORD`, `HOST`, `PORT`, `FLASK_DEBUG`, and for the parser `PARSE_SPLIT_TIMEOUT`, `PARSE_TOTAL_TIMEOUT`, `MAX_TEXT_LENGTH`. With an empty `MONGO_DB_PASSWORD` the client connects without auth. The Mongo client is lazy (`connect=False`), so the server starts and parser/transliteration queries work with no DB; only dictionary queries need MongoDB.

Startup takes a few seconds: `parser_service.py` builds one `LexicalSandhiAnalyzer` (both lexicons) at import time. In debug mode the reloader does this twice.

## Architecture

- `app.py` → imports `sanskrit_utils.app` (Flask). Also the uWSGI module (`app:app`) in Docker.
- `sanskrit_utils/schema/` — schema-first Ariadne. All `*.graphql` files in this directory are loaded and merged (`schema.graphql` defines base `Query`/`Mutation`; others use `extend type`). Resolvers are Python modules that import the shared `query`/`mutation` ObjectTypes from `sanskrit_utils.schema` and register with `@query.field(...)`.
  - **Import order in `schema/__init__.py` matters**: `Query`/`Mutation` must be imported before `Sanscript`/`sans_parser`, which import them back from the package (circular by design). A new resolver module must be imported there, and any new ObjectType/EnumType bindables added to `type_resolvers`.
  - `Sanscript.py` — `SanscriptScheme` and `Dictionaries` Python enums bound to GraphQL enums (resolvers receive enum members; use `.value`). Holds transliteration plus dictionary search/browse/CRUD resolvers. Resolvers inspect `info.field_nodes` to fetch or compute only the requested fields.
  - `sans_parser.py` — thin resolvers for the parser queries (`splits`, `splitPairs`, `joins`, `tags`, `presegmented`, `parse`, `dhatus`, `maheshvaraSutras`, `pratyahara`, `meter`). Register them with `@parser_field(name)`, which turns `parser_service.InputError` into a GraphQL error. Argument defaults are declared in the SDL; resolvers still treat an explicit `null` as the default. `Parse`/`ParseItem` values are service objects whose fields are read as attributes, plus a few field resolvers for the DOT fields that take a `scheme` argument.
- `sanskrit_utils/parser_service.py` — all `sanskrit_parser`/`sanskrit_util` work, with no GraphQL in it. SLP1 strings in and out; `to_slp1`/`from_slp1` at the edges. It deliberately does **not** use `sanskrit_parser.Parser`/`Split.parse`, because of upstream bugs that `tests/test_lib_*.py` pin as `xfail(strict=True)`:
  - `normalize()` replaces upstream's input normalisation (which breaks `saMyoga`-type words and ignores anusvara in strict mode). `strictIO` means: input as typed, and word forms in the output keep a final `s`/`r` instead of visarga. Only word forms are denormalised on output, never roots, tags or relation names.
  - `_best_paths()` replaces `SandhiGraph.find_all_paths`, whose result for the same text changes between calls.
  - `SplitAnalysis` works on each split lazily, on its own word objects (upstream shares them between splits and accumulates tags), in two steps. Building the graph of possible relations is quick and never starts a search (`_unsearched`, a `_BudgetedVakyaGraph` with no deadline); it serves `splitDot` and `analysisSplitDot` (`relations`). The search for analyses (`_analysed`) runs only for `status`/`analysis`/`parseDots` and under a `ParseBudget`; `_BudgetedVakyaGraph` stops it at the deadline. An 11-word sentence takes ~5s; many longer ones never finish and return `status: TIMEOUT`.
  - `Dhatupatha` replaces upstream's `DhatuWrapper` (it is installed as `sanskrit_parser.parser.datastructures.dw`, which `VakyaGraph` consults for transitivity). Upstream answers "intransitive" for any root it cannot find by exact name, which is ~29% of the lexicon's verb roots, so those verbs never get a `karma` and their sentences have no analysis. `Dhatupatha` also tries an `-A` root as `-E`/`-o` (`DyA` → `DyE`). A root that is still unknown stays intransitive unless the query passes `unknownRootsTransitive: true`; that is a `ContextVar` set around graph construction in `SplitAnalysis._graph` (the instance is shared by all requests, so it must not be an attribute).
  - `SplitAnalysis.relations(by_head)` (the `analysisSplitDot.graph` rows) merges readings: one row per node `(index, pada, root)` + `sambandha` (+ head `(index, pada, root)` when `by_head`), tags unioned. The `SplitGraph.graph` resolver passes `by_head` according to whether the query selects `predecessor` (`_selects` walks fragments).
  - The sandhi analyzer keeps per-call state on itself, so `_split_slp1` holds `_analyzer_lock`. Nothing else is shared between requests.
  - Anything sorted for output must not rely on `str()` of upstream nodes or on set order (both vary per run); use `_node_key`.
- `tests/` — pytest. `test_api_*.py` run queries through the `gql`/`gql_error` fixtures (schema executed in-process), `test_parser_service.py` covers the service, `test_lib_*.py` test the two libraries directly. An `xfail(strict=True)` test that starts passing means an upstream bug is fixed and its workaround (named in the reason) can be removed; re-check these when bumping the `sanskrit-parser` commit in `requirements.txt`.
- `sanskrit_utils/database.py` — env-configured pymongo client. The API reads collections `dictEntries` and `dictPhonetics`.
- `sanskrit_utils/loaders/` — standalone one-off ETL scripts, not imported by the API. Run them from the **repo root** as `python sanskrit_utils/loaders/<X>.py`: they read source SQLite dictionaries from `tmp/<dict>.sqlite` (gitignored, local only) and use sibling imports (`from utils import ...`).
  - `LexiconDicToMongodb.py`, `SanDicDhatuPataToMongodb.py`, `SetupMongoDb.py` (indexes), `ParseDictEntries.py` (builds `dictPhonetics`) target the API's `dictEntries`.
  - `DevHub*` loaders write a **different** collection, `DictWords`, in a different document shape, for a separate "devhub" app. Per README, `DevHubLexiconDicToMongodb.py` is the one that supports all current dictionaries.
- Dictionary documents: `word`/`desc` are dicts keyed by scheme (`slp1`, `devanagari`, …), plus `wordOriginal`, `descOriginal`, `origin` (a `Dictionaries` value), and `wordIndex`. Search runs on `word.slp1`/`desc.slp1` (text index + regex); input is transliterated to SLP1 first.

## Deployment

- `Dockerfile` (prod): nginx (`docker/nginx.conf`, :80) → uWSGI unix socket (`docker/uwsgi.ini`), launched by `docker/start.sh`. `Dockerfile.dev` runs `app.py` on :5000.
- `.github/workflows/docker-publish.yml` pushes to `ghcr.io/<repo>`. Tags `vX.Y.Z` produce image tags `X.Y.Z`, `X.Y`, `X` (if X>0) and `latest`, plus a GitHub Release. Branch pushes produce `master`/`sha-*` images. PRs only build.
- Legacy pipeline that still exists: `.drone.yml` builds to a private registry and runs `.ansible/playbook.yml` (k8s deployment template, vault-encrypted vars).
