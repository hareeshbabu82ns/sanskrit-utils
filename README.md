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

One endpoint, `/graphql`. Every argument and its default is documented in the
explorer at `GET /graphql`. Text arguments take `schemeFrom` (default
`DEVANAGARI`) and results come back in `schemeTo` (default `SLP1`).

`strictIO` (default `false`) controls how text is read and written:

- `false`: punctuation, digits and dandas are dropped, a final visarga or
  anusvara is read the way the lexicon spells it, and word forms in the result
  show a final `s`/`r` as visarga.
- `true`: the text is taken as typed, and word forms in the result keep the
  final `s`/`r` the parser works with (so `rAmas` and `punar` stay distinct).

In both modes anusvara before a stop is read as the class nasal
(`శుక్లాంబర` = `SuklAmbara`), because that is the only spelling the lexicon has.

- convert text between schemes

```graphql
{
  transliterate(text: "harIS", schemeFrom: SLP1, schemeTo: DEVANAGARI)
}
```

- dictionary search (needs MongoDB)

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

- dictionary browse (needs MongoDB)

```graphql
{
  dictionaryBrowse(
    browseWith: { origin: VCP, outputScheme: TELUGU, limit: 10, offset: 2 }
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

- sandhi split of a sentence, best splits first

```graphql
{
  splits(
    text: "कालिदासस्य जीवनवृत्तिविषये अनेकाः लोकविश्रुतयः अनेके वादाः च सन्ति"
    schemeTo: TELUGU
    limit: 2
  )
}
```

- two-part sandhi decompositions of one word, straight from the rules
  (`tasminniti` → `tasmin` + `iti`); `valid` marks pairs of real words

```graphql
{
  splitPairs(text: "तस्मिन्निति", schemeTo: IAST, validOnly: true) {
    left
    right
    valid
  }
}
```

- sandhi join of two or more words (every form the rules allow)

```graphql
{
  joins(words: ["కాలి", "దాసస్య"], schemeFrom: TELUGU, schemeTo: TELUGU)
}
```

- morphological tags of a word, or of each word of a text

```graphql
{
  tags(text: "కాలిదాసస్య", schemeFrom: TELUGU, schemeTo: TELUGU) {
    form
    word
    tags
  }
}
```

`lexicon: INRIA | SANSKRIT_DATA | COMBINED` picks the word list (default `COMBINED`).

- words of a sentence that is already split

```graphql
{
  presegmented(text: "దేవదత్తః గ్రామం గచ్ఛతి", schemeFrom: TELUGU, schemeTo: TELUGU)
}
```

- sentence analysis: sandhi split, then the relations between the words

```graphql
{
  parse(
    text: "శుక్లాంబరధరం విష్ణుం శశివర్ణం చతుర్భుజమ్"
    schemeFrom: TELUGU
    schemeTo: TELUGU
    limit: 2
  ) {
    split
    status
    analysis {
      cost
      graph {
        node {
          index
          pada
          root
          tags
        }
        predecessor {
          index
          pada
        }
        sambandha
      }
      dot
      dotURL
      conll
    }
    analysisSplitDot {
      graph {
        node {
          index
          pada
          root
          tags
        }
        predecessor {
          index
          pada
        }
        sambandha
      }
    }
    splitDot
    splitDotURL
  }
}
```

`limit` caps the sandhi splits, `parseLimit` (default 2) the analyses per
split, `minCostOnly` keeps only the cheapest analyses, and `preSegmented: true`
analyses the text as it stands. `status` is `OK`, `NO_PARSE` (no analysis
connects all the words) or `TIMEOUT`. DOT text follows `schemeTo`; pass
`scheme` to a DOT field to override it, e.g. `splitDotURL(scheme: IAST)`.

Each split is worked on in two steps, and only as far as the selected fields
need:

1. Finding every relation that is possible between the words. This is quick.
   `splitDot` draws the result and `analysisSplitDot` gives the same thing in
   the shape of an `analysis` entry. It is not a tree: a word has a `graph`
   row for each relation it could be in. Rows with the same `index`, `pada`,
   `root` and `sambandha` are merged into one whose `tags` are those of all
   the readings. If `predecessor` is selected, rows are also kept apart by
   the word depended on. Use it when `analysis` comes back empty.
2. Searching those relations for the trees that connect every word. `status`,
   `analysis`, `parseDots` and `parseDotURLs` need this step. The time it
   takes grows very fast with the length of the sentence: seconds for about
   ten words, and often more than is reasonable beyond that.
   `PARSE_SPLIT_TIMEOUT` (seconds per split, default 10) and
   `PARSE_TOTAL_TIMEOUT` (seconds per query, default 30) bound it; a split
   that runs out of time has `status: TIMEOUT` and an empty `analysis`.

A long sentence can have thousands of analyses and the cheapest is not always
the intended one; raise `parseLimit` to see more of them.

Whether a verb can take an object is looked up in the dhatupatha by the root
that `tags` reports. About a quarter of those roots are not found there
(`stu`, `praS`, `mokz`); such a verb is treated as intransitive, so a sentence
that gives it an object gets `NO_PARSE`. Pass `unknownRootsTransitive: true`
to let those verbs take an object. More sentences are analysed that way, and
so are more splits that are not what the text means.

- dhatupatha entries of a root, by its name (`gam`), its taught form
  (`gamx~`) or the name `tags` gives it (`DyA` for `DyE`)

```graphql
{
  dhatus(dhatu: "कृ", schemeTo: DEVANAGARI) {
    dhatu
    mulaDhatu
    artha
    gana
    pada
    karmakatva
    sakarmaka
    ittva
    rupa
  }
}
```

- Maheshvara sutras and pratyaharas

```graphql
{
  maheshvaraSutras
  pratyahara(name: "अच्", schemeTo: DEVANAGARI, withLongVowels: true) {
    name
    varnas
  }
}
```

- guru/laghu scansion of a verse, line by line

```graphql
{
  meter(text: "शुक्लाम्बरधरं विष्णुं शशिवर्णं चतुर्भुजम् ।", schemeTo: IAST) {
    text
    syllables
    pattern
  }
}
```

#### Tests

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest              # no MongoDB or network needed
.venv/bin/python -m pytest -k parse     # a subset
```

`tests/test_api_*.py` run GraphQL queries against the schema,
`tests/test_parser_service.py` covers the service layer, and
`tests/test_lib_*.py` test `sanskrit_parser` and `sanskrit_util` directly.
Tests reported as `xfail` describe known bugs in those two libraries; one that
starts passing (reported as a failure) means the bug is fixed upstream and the
workaround named in its reason can go.

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
