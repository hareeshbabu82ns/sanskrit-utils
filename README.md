# Samskrutam Utilities
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
$> python run.py

# run using flask module
$> python -m flask run
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

$> docker image prune -a
$> docker exec -it sanskrit-utils /bin/bash
$> docker logs -f sanskrit-utils

# after the CI build, deploy docker image
$> docker run -d --restart on-failure -p 5000:80 --name sanskrit-utils docker.terabits.io/home/sanskrit-utils:latest
```