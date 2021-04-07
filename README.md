# Samskrutam Utilities [![Drone Build Status](https://drone.terabits.io/api/badges/hareeshbabu82ns/sanskrit-utils/status.svg)](https://drone.terabits.io/hareeshbabu82ns/sanskrit-utils)
Contains Utilities to help learning Samskrutam

* **sanskrit_parser** is helpful in splitting and adding the words
* **dictionaries** is an interface for various dictionories

#### Setting up for Development
```sh
# create virtual env
$> virtualenv venv

# activate virtual env
$> venv
# or
$> source venv/bin/activate

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
* Development mode
```sh
$> docker build -f Dockerfile.dev --tag sanskrit-utils .
$> docker run -d -p 5000:5000 --name sanskrit-utils sanskrit-utils
```

* Production mode
```sh
$> docker build --tag sanskrit-utils .
$> docker tag sanskrit-utils:latest sanskrit-utils:v1.0.0
$> docker rmi sanskrit-utils:v1.0.0
$> docker run -d -p 5000:80 --name sanskrit-utils sanskrit-utils
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

#### API
* convert text between schemes
```graphql
{
  transliterate(text:"harIS",schemeFrom:SLP1,schemeTo:DEVANAGARI)
}
```

* dictionary full text (fuzzy) search
```graphql
{
    dictionaryFuzzySearch(search:"rama",origin:[DHATU_PATA]){
        key
        description
        origin
    }
}
```

#### Issues