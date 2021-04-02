#!/usr/bin/env python

from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()


setup_options = dict(name='sanskrit_utils',
                     version='0.0.1',
                     author='Hareesh Polla',
                     author_email='hareeshbabu82@gmail.com',
                     install_requires=required,
                     packages=find_packages())

setup(**setup_options)
