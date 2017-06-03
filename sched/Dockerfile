FROM bitnami/minideb:jessie
 
MAINTAINER l.morales@bbva.com

# expose port
#EXPOSE $PORTS

# copy the contents of the `app/` folder into the container at build time
ADD pymesos/ /pymesos/
# copy the contents of the `app/` folder into the container at build time
ADD app/ /app/

#run commands:
RUN apt-get update && apt-get install -y python3 python-dev python3-dev python-pip libzookeeper-mt-dev \
    && pip install virtualenv \
    # create a virtualenv we can later use
    && mkdir -p /venv/ \
    # install python version on virtual environment
    && virtualenv -p /usr/bin/python2.7 /venv
    #activate virtual environment

RUN . /venv/bin/activate \
    # install python dependencies into venv
    && pip install -r /pymesos/requirements.txt --upgrade \
    && pip install /pymesos/lib/pymesos-0.2.13.tar.gz \
    && pip install redis \
    && pip install hiredis \
    # clean cache
    && apt-get clean -y && \
    apt-get autoclean -y && \
    apt-get autoremove -y && \

    rm -rf /usr/share/locale/* && \
    rm -rf /var/cache/debconf/*-old && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /usr/share/doc/*

RUN chmod a+x /app/scheduler.sh

ENV MASTER 172.16.48.181
ENV DOCKER_TASK luismorales/pymesos-exec:4.0
ENV MAX_TASKS 5
ENV REDIS_SERVER redis.marathon.l4lb.thisdcos.directory

# CMD source /venv/bin/activate
