# Simple Dockerfile to execute redis-commander from docker
FROM node

RUN mkdir -p /usr/src
WORKDIR /usr/src

RUN git clone https://github.com/joeferner/redis-commander.git \
	&& cd redis-commander \
	&& npm install -g redis-commander

ENV REDIS-SERVER redis.marathon.l4lb.thisdcos.directory	

ENTRYPOINT [ "redis-commander" ]

EXPOSE 8081 