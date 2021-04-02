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