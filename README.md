# Samskrutam Utilities [![Drone Build Status](https://drone.terabits.io/api/badges/hareeshbabu82ns/sanskrit-utils/status.svg)](https://drone.terabits.io/hareeshbabu82ns/sanskrit-utils)

Contains Utilities to help learning Samskrutam

- **sanskrit_parser** is helpful in splitting and adding the words
- **dictionaries** is an interface for various dictionories

#### submitting with git tag

```sh
# Increment patch version (vX.X.X+1)
./tag_version.py patch

# Increment minor version (vX.X+1.0)
./tag_version.py minor

# Increment major version (vX+1.0.0)
./tag_version.py major
```

#### Setting up for Development

```sh
$> apt install python3-virtualenv

# create virtual env
$> python3 -m virtualenv .venv

# activate virtual env
$> .venv
# or
$> source .venv/bin/activate

# deactivate virtual env
$> deactivate

# write requirements.txt
$> pip freeze > requirements.txt

# install packages from requiremnts.txt
$> pip install -r requirements.txt
```

#### Running sample API

```sh
$> python api_test.py
```

#### Building and Running locally

```sh
$> PYTHONPATH=. python setup.py install
$> python app.py

# run using flask module
$> MONGO_DB_PASSWORD=pwd  \
    MONGO_DB_HOST=192.168.0.10  \
    MONGO_DB_PORT=3333  \
    python -m flask run
```

#### Building and Running Docker

- Development mode

```sh
$> docker build -f Dockerfile.dev --tag sanskrit-utils .
$> docker run -d -p 5000:5000 --name sanskrit-utils sanskrit-utils
```

- Production mode

```sh
$> docker build --tag sanskrit-utils .
$> docker tag sanskrit-utils:latest sanskrit-utils:v1.0.0
$> docker rmi sanskrit-utils:v1.0.0
$> docker run -d -p 5000:80 \
    -e MONGO_DB_PASSWORD= \
    -e MONGO_DB_HOST= \
    -e MONGO_DB_PORT= \
    --name sanskrit-utils sanskrit-utils
$> docker rm -f sanskrit-utils

$> docker image prune -a
$> docker exec -it sanskrit-utils /bin/bash
$> docker logs -f sanskrit-utils

# after the CI build, deploy docker image
$> docker run -d --restart on-failure -p 5000:80 --name sanskrit-utils docker.terabits.io/home/sanskrit-utils:latest
```

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
