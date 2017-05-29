#!/usr/bin/env python2.7
from __future__ import print_function

import sys
import uuid
import time
import socket
import signal
import getpass
from threading import Thread
from os.path import abspath, join, dirname
import os

from pymesos import MesosSchedulerDriver, Scheduler, encode_data
from addict import Dict

TASK_CPU = 1
TASK_MEM = 32
EXECUTOR_CPUS = 1
EXECUTOR_MEM = 32


class MinimalScheduler(Scheduler):

    def __init__(self,message):
        self._message = message

    def resourceOffers(self, driver, offers):
        filters = {'refuse_seconds': 5}

        for offer in offers:
            cpus = self.getResource(offer.resources, 'cpus')
            mem = self.getResource(offer.resources, 'mem')
            if cpus < TASK_CPU or mem < TASK_MEM:
                continue

            task = Dict()
            task_id = str(uuid.uuid4())
            task.task_id.value = task_id
            task.agent_id.value = offer.agent_id.value
            task.name = 'task {}'.format(task_id)
#            task.container.type = 'MESOS'
            task.container.type = 'DOCKER' 
#            task.container.docker.image.type = 'DOCKER'
#            task.container.docker.image.docker.name = 'luismorales/pymesos-exec:2.0'
            task.container.docker.image = os.getenv('DOCKER_TASK')
            task.container.docker.network = 'HOST'
            task.container.docker.force_pull_image = True
            #task.executor = self.executor
#            task.data = encode_data('Hello from task {}!'.format(task_id))

            task.resources = [
                dict(name='cpus', type='SCALAR', scalar={'value': TASK_CPU}),
                dict(name='mem', type='SCALAR', scalar={'value': TASK_MEM}),
            ]

            task.command.shell = True
            task.command.value = '/app/task.sh '+self._message
#            task.command.arguments = [self._message]
            
            driver.launchTasks(offer.id, [task], filters)

    def getResource(self, res, name):
        for r in res:
            if r.name == name:
                return r.scalar.value
        return 0.0

    def statusUpdate(self, driver, update):
        logging.debug('Status update TID %s %s',
                      update.task_id.value,
                      update.state)


def main(message):
#   executor = Dict()
#   executor.executor_id.value = 'MinimalExecutor'
#   executor.name = executor.executor_id.value
#   executor.command.value = '. /app/executor.sh'
#    executor.resources = [
#        dict(name='mem', type='SCALAR', scalar={'value': EXECUTOR_MEM}),
#        dict(name='cpus', type='SCALAR', scalar={'value': EXECUTOR_CPUS}),
#    ]
#    executor.container.type = 'MESOS'
#    executor.container.mesos.image.type = 'DOCKER'
#    executor.container.mesos.docker.image = 'luismorales/pymesos-exec:2.0'

    framework = Dict()
    framework.user = getpass.getuser()
    framework.name = "MinimalFramework"
    framework.hostname = socket.gethostname()

    driver = MesosSchedulerDriver(
        MinimalScheduler(message),
        framework,
        os.getenv('MASTER'),
        use_addict=True,
    )

    def signal_handler(signal, frame):
        driver.stop()

    def run_driver_thread():
        driver.run()

    driver_thread = Thread(target=run_driver_thread, args=())
    driver_thread.start()

    print('master: {}'.format(os.getenv('MASTER')))
    print('Scheduler running, Ctrl+C to quit.')
    signal.signal(signal.SIGINT, signal_handler)

    while driver_thread.is_alive():
        time.sleep(1)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) != 2:
        print("Usage: {} <message>".format(sys.argv[0]))
        sys.exit(1)
    else:
        main(sys.argv[1])
