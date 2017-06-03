from __future__ import print_function
import sys
import uuid
import time
import socket
import signal
import getpass
from threading import Thread
import os
import redis, hiredis

from pymesos import MesosSchedulerDriver, Scheduler, encode_data
from addict import Dict

TASK_CPU = 0.2
TASK_MEM = 32
EXECUTOR_CPUS = 1
EXECUTOR_MEM = 32


class MinimalScheduler(Scheduler):
    def __init__(self, message, conn):
        self._redis = conn
        self._message = message

    def registered(self, driver, frameworkId, masterInfo):
        #set max tasks to framework registered
        logging.info("************registered     " + frameworkId['value'])
        self._redis.hset(os.getenv('MARATHON_APP_ID'), 'max_tasks', int(os.getenv('MAX_TASKS')))
        self._redis.hset(os.getenv('MARATHON_APP_ID'),'fwk_id',frameworkId['value'])
        #logging.info(masterInfo)
        #logging.info(driver)
        logging.info("<---")

    def reregistered(self, driver, masterInfo):
        logging.info("************re-registered  ")
        logging.info(masterInfo)
        #logging.info(self)
        logging.info(driver)
        logging.info("<---")

    def checkTask(self, frameworkId):

        if int(self._redis.hget(os.getenv('MARATHON_APP_ID'),'max_tasks')) <= 0:
            logging.info("maximum number of tasks")
            raise Exception('maximum number of tasks')
        else:
            logging.info("number tasks available = "+self._redis.hget(os.getenv('MARATHON_APP_ID'),'max_tasks') + " of " + os.getenv("MAX_TASKS") )
            self._redis.hincrby(os.getenv('MARATHON_APP_ID'),'max_tasks',-1)
        #logging.info(framework)
        #logging.info(_redis.get('foo'))
        # queue????
        #self._redis.decr('foo')
        #if self._redis.get('foo') < 0:
         #   raise Exception('maximum number of tasks')

    def resourceOffers(self, driver, offers):
        filters = {'refuse_seconds': 5}
        for offer in offers:
            try:
                self.checkTask(driver.framework_id)
                cpus = self.getResource(offer.resources, 'cpus')
                mem = self.getResource(offer.resources, 'mem')
                if cpus < TASK_CPU or mem < TASK_MEM:
                    continue

                task = Dict()
                task_id = str(uuid.uuid4())
                task.task_id.value = task_id
                task.agent_id.value = offer.agent_id.value
                task.name = 'task {}'.format(task_id)
                task.container.type = 'DOCKER'
                task.container.docker.image = os.getenv('DOCKER_TASK')
                task.container.docker.network = 'HOST'
                task.container.docker.force_pull_image = True

                task.resources = [
                    dict(name='cpus', type='SCALAR', scalar={'value': TASK_CPU}),
                    dict(name='mem', type='SCALAR', scalar={'value': TASK_MEM}),
                ]
                task.command.shell = True
                task.command.value = '/app/task.sh ' + self._message
                # task.command.arguments = [self._message]
                #logging.info(task)
                logging.info("launch task name:" + task.name + " resources: "+ ",".join(str(x) for x in task.resources))
                driver.launchTasks(offer.id, [task], filters)
            except Exception:
                #traceback.print_exc()
                pass

    def getResource(self, res, name):
        for r in res:
            if r.name == name:
                return r.scalar.value
        return 0.0

    def statusUpdate(self, driver, update):
        logging.debug('Status update TID %s %s',
                      update.task_id.value,
                      update.state)
        if update.state == "TASK_FINISHED":
            logging.info("take another task for framework" + driver.framework_id)
            self._redis.hincrby(os.getenv('MARATHON_APP_ID'),'max_tasks',1)
            logging.info("tasks availables = " + self._redis.hget(os.getenv('MARATHON_APP_ID'),'max_tasks')+ " of "+os.getenv("MAX_TASKS"))
            
    
def main(message):
    connection = redis.StrictRedis(host=os.getenv('REDIS_SERVER'), port=6379, db=0)
    framework = Dict()
    framework.user = getpass.getuser()
    framework.name = "MinimalFramework"
    framework.hosthname = socket.gethostname()
    if connection.hexists(os.getenv('MARATHON_APP_ID'),'fwk_id'):
        logging.info("framework id already registered in redis")
        framework._id = connection.hget(os.getenv('MARATHON_APP_ID'),'fwk_id')

    driver = MesosSchedulerDriver(
        MinimalScheduler(message, connection),
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