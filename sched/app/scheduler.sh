#!/bin/bash

#_term() { 
#  echo "Caught SIGTERM signal!" 
#}

#trap _term SIGTERM

. /venv/bin/activate
#python /app/scheduler.py $1 $2 $3 $4 $5 &
exec python /app/scheduler.py $1 $2 $3 $4 $5

#child=$! 
#wait "$child"