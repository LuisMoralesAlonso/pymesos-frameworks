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
    def __init__(self, message, master, task_imp, max_tasks, connection, fwk_name):
        self._redis = connection
        self._message = message
        self._master = master
        self._max_tasks = max_tasks
        self._task_imp = task_imp
        self._fwk_name = fwk_name

    def registered(self, driver, frameworkId, masterInfo):
        #set max tasks to framework registered
        logging.info("************registered     ")
        self._redis.hset(self._fwk_name, 'max_tasks', int(self._max_tasks))
        logging.info(frameworkId)
        self._redis.hset(self._fwk_name,'fwk_id', frameworkId['value'])
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
        if int(self._redis.hget(self._fwk_name,'max_tasks')) <= 0:
            logging.info("Reached maximum number of tasks")
            raise Exception('maximum number of tasks')
        else:
            logging.info("number tasks available = "+self._redis.hget(self._fwk_name,'max_tasks') + " of " + self._max_tasks)
            self._redis.hincrby(self._fwk_name,'max_tasks',-1)
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
                task.container.docker.image = self._task_imp
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
            self._redis.hincrby(self._fwk_name,'max_tasks',1)
            logging.info("tasks availables = " + self._redis.hget(self._fwk_name,'max_tasks')+ " of "+self._max_tasks)
            
    
def main(message, master, task_imp, max_tasks, redis_server):
    connection = redis.StrictRedis(host=redis_server, port=6379, db=0)
    framework = Dict()
    framework.user = getpass.getuser()
    framework.name = "MoralesMinimalFramework"
    framework.hostname = socket.gethostname()
    if connection.hexists(framework.name,'fwk_id'):
        logging.info("framework id already registered in redis")
        framework.id = dict(value=connection.hget(framework.name,'fwk_id'))

    driver = MesosSchedulerDriver(
        MinimalScheduler(message, master, task_imp, max_tasks, connection, framework.name),
        framework,
        master,
        use_addict=True,
    )

    def signal_handler(signal, frame):
        logging.info("Closing redis connection, cleaning scheduler data and stopping MesosSchdulerDriver")
        logging.info("Stop driver")
        driver.stop()

    def run_driver_thread():
        driver.run()

    driver_thread = Thread(target=run_driver_thread, args=())
    driver_thread.start()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    while driver_thread.is_alive():
        time.sleep(1)

    logging.info("Borramos redis")
    connection.delete(framework.name)
 
    logging.info("Disconnect from redis")
    connection.disconnect()
    connection = None    

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) != 6:
        print("Usage: {} <message> <master> <task> <max_tasks> <redis_server>".format(sys.argv[0]))
        sys.exit(1)
    else:
        main(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5])        