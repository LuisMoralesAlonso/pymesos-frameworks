#!/bin/bash
# create a virtualenv we can later use
#mkdir -p /venv/
# install python version on virtual environment
#virtualenv -p /usr/bin/python$VERSION /venv
#activate virtual environment
#source /venv/bin/activate
# install python dependencies into venv
#pip install -r /app/requirements.txt --upgrade
#pip install /app/lib/pymesos-0.2.13.tar.gz
# run our app inside the container http://172.16.48.181
#/app/app.py 172.16.48.181
#docker run -e VERSION=2.7 -e MASTER_IP=172.16.48.181 -v /home/rbravo/datio/techlab/python-docker/app:/opt prueba /opt/app.

. /venv/bin/activate
python /app/scheduler.py $1	
