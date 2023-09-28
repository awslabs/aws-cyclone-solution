#!/bin/bash

#start nginx server
nginx -g 'daemon off;' &

# start flask server
FLASK_APP=$PWD/api/endpoints.py python -m flask run --port 4433