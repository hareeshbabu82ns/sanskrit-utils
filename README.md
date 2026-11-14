# Samskrutam Utilities [![Drone Build Status](https://drone.terabits.io/api/badges/hareeshbabu82ns/sanskrit-utils/status.svg)](https://drone.terabits.io/hareeshbabu82ns/sanskrit-utils)

Contains Utilities to help learning Samskrutam

- **sanskrit_parser** is helpful in splitting and adding the words
- **dictionaries** is an interface for various dictionories

- currently `DevHubLexiconDicToMongodb.py` supports all dictionaries collected so far

#### Totals

- last calculated:
  - total records: `927606`
  - unique words (individual): `782014`
  - total unique words: `364949`

```
    Dictionary  Row Count  Unique Row Count
15          mw     287443            193914
17        mw72      55388             51154
23         vcp      50134             48635
20         shs      47312             46707
26         yat      45206             44720
25         wil      44578             43939
21         skd      42531             40817
7          cae      40069             38484
1          acc      49822             32576
2         ap90      32176             31703
28      eng2te      31568             29772
16         mwe      32378             28239
4          bor      24608             22012
14          md      20749             20103
6          bhs      17839             17777
5          ben      17310             17036
19         pui      17512             11740
0           ae      11364             11347
10         inm      12647              9454
9          ieg       7907              7567
8          gst       6780              6761
3         armh       7907              6673
18          pe       8799              6625
12         lan       4944              4726
24         vei       3834              3704
13         mci       2643              2325
11         krm       2061              1698
29  dhatu_pata       1159               888
27         pgn        485               470
22         snp        453               448
```

#### Running locally

```sh
cp .env.example .env   # set MONGO_DB_* (optional: transliterate/parser queries work without MongoDB)
./run.sh               # creates .venv if missing, installs requirements, starts the API
./run.sh --install     # only set up .venv / install requirements
```

The GraphQL explorer is at `http://127.0.0.1:5000/graphql`.

#### Building and Running Docker

```sh
# development (flask dev server on :5000)
docker build -f Dockerfile.dev --tag sanskrit-utils:dev .
docker run -d -p 5000:5000 --name sanskrit-utils sanskrit-utils:dev

# production (nginx + uWSGI on :80)
docker build --tag sanskrit-utils .
docker run -d -p 5000:80 \
    -e MONGO_DB_PASSWORD= \
    -e MONGO_DB_HOST= \
    -e MONGO_DB_PORT= \
    --name sanskrit-utils sanskrit-utils
```

#### Releasing

```sh
scripts/release.py patch      # vX.Y.Z -> vX.Y.Z+1
scripts/release.py minor      # vX.Y.Z -> vX.Y+1.0
scripts/release.py major      # vX.Y.Z -> vX+1.0.0
scripts/release.py patch --dry-run
```

Pushing the tag triggers `.github/workflows/docker-publish.yml`, which pushes
`ghcr.io/hareeshbabu82ns/sanskrit-utils:{X.Y.Z, X.Y, X, latest}` and creates a
GitHub Release with generated notes. Pushes to `master` publish `master` and
`sha-<short>` images; pull requests only build.

#### Converting Dictionaries

```sh
$> MONGO_DB_PASSWORD=pwd  \
    MONGO_DB_HOST=192.168.0.10  \
    MONGO_DB_PORT=3333  \
    python sanskrit_utils/loaders/SanDicDhatuPataToMongodb.py

$> MONGO_DB_PASSWORD=pwd  \
    MONGO_DB_HOST=192.168.0.10  \
    MONGO_DB_PORT=3333  \
    python sanskrit_utils/loaders/LexiconDicToMongodb.py
```

#### Inital Setup

- sets up indexes

```sh
$> MONGO_DB_PASSWORD=sansutils \
 MONGO_DB_HOST=192.168.0.10 \
 MONGO_DB_PORT=3333 \
 python sanskrit_utils/loaders/SetupMongoDb.py
```

##### Running Ansible Playbook from local

- enable line `ansible_ssh_private_key_file: "~/.ssh/id_rsa_hsrv"` in `hosts.yml`
- run `ansible-playbook playbook.yml --extra-vars "commit_sha=3333 git_branch=main git_repo=devhub"`

#### API

- convert text between schemes

```graphql
{
  transliterate(text: "harIS", schemeFrom: SLP1, schemeTo: DEVANAGARI)
}
```

- dictionary search

```graphql
{
  dictionarySearch(
    searchWith: {
      search: "idAm"
      searchScheme: SLP1
      fuzzySearch: false
      startsWith: false
      endsWith: false
      searchOnlyKeys: false
      origin: [VCP]
      outputScheme: TELUGU
      limit: 10
      offset: 2
    }
  ) {
    total
    results {
      id
      key
      description
      origin
    }
  }
}
```

- dictionary Browse

```graphql
{
  dictionaryBrowse(
    searchWith: { origin: VCP, outputScheme: TELUGU, limit: 10, offset: 2 }
  ) {
    total
    results {
      id
      key
      description
      origin
    }
  }
}
```

- vaakya split

```graphql
{
  splits(
    text: "कालिदासस्य जीवनवृत्तिविषये अनेकाः लोकविश्रुतयः अनेके वादाः च सन्ति"
    schemeTo: TELUGU
    limit: 2
    strictIO: false
  )
}
```

- word joins (sandhi)

```graphql
{
  joins(
    words: ["కాలి", "దాసస్య"]
    schemeFrom: TELUGU
    schemeTo: TELUGU
    strictIO: false
  )
}
```

- word tags

```graphql
{
  tags(text: "కాలిదాసస్య", schemeFrom: TELUGU, schemeTo: TELUGU) {
    word
    tags
  }
}
```

- presegmented tags

```graphql
{
  presegmented(
    text: "దేవదత్తః గ్రామం గచ్ఛతి"
    schemeFrom: TELUGU
    schemeTo: TELUGU
  )
}
```

- presegmented parser tags

```graphql
{
  parse(text: "देवदत्तः ग्रामं गच्छति", schemeTo: TELUGU) {
    parseDots
    parseDotURLs
    splitDot
    splitDotURL
    analysis {
      graph {
        node {
          pada
          root
          tags
        }
        predecessor {
          pada
          root
          tags
        }
        sambandha
      }
    }
  }
}
```

#### Indexes

```js
[
  { v: 2, key: { _id: 1 }, name: "_id_" },
  {
    v: 2,
    key: { _fts: "text", _ftsx: 1 },
    name: "fts",
    background: false,
    weights: { "desc.slp1": 1, "word.slp1": 1 },
    default_language: "english",
    language_override: "language",
    textIndexVersion: 3,
  },
  { v: 2, key: { origin: 1, word: 1 }, name: "dict_browse", background: false },
  { v: 2, key: { wordOriginal: 1 }, name: "wordOriginal_1", background: false },
  { v: 2, key: { "word.slp1": 1 }, name: "word.slp1_1", background: false },
  { v: 2, key: { descOriginal: 1 }, name: "descOriginal_1", background: false },
  { v: 2, key: { "desc.slp1": 1 }, name: "desc.slp1_1", background: false },
];
```

#### Issues
