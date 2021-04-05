#!/usr/bin/env bash
service nginx start
flask initdb
uwsgi --ini uwsgi.ini