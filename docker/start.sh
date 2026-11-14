#!/usr/bin/env bash
service nginx start
exec uwsgi --ini docker/uwsgi.ini
