from __future__ import print_function
import sys
import uuid
import time
import socket
import signal
import getpass
from threading import Thread, Timer
import os
import redis, hiredis
from pymesos import MesosSchedulerDriver, Scheduler, encode_data
from addict import Dict
import rhelper, constants


class MinimalScheduler(Scheduler):
    def __init__(self, message, master, task_imp, max_tasks, connection, fwk_name):
        self._redis = connection
        self._message = message
        self._master = master
        self._max_tasks = max_tasks
        self._task_imp = task_imp
        self._fwk_name = fwk_name
        self._helper=rhelper.Helper(connection,fwk_name)
        self.accept_offers = True
        self._timers = {}

    def registered(self, driver, frameworkId, masterInfo):
        logging.info("************registered     ")
        self._helper.register(frameworkId['value'],masterInfo)
        logging.info("<---")

    def reregistered(self, driver, masterInfo):
        logging.info("************re-registered  ")
        self._helper.reregister(masterInfo)
        driver.suppressOffers()
        driver.reconcileTasks([])
        #Must include a flag to indicate that tasks reconciliation has finished
        driver.reviveOffers()
        logging.info("<---")

    def resourceOffers(self, driver, offers):
        filters = {'refuse_seconds': 5}
        for offer in offers:
            try:
                #self.checkTask(driver.framework_id)
                self._helper.checkTask(self._max_tasks)
                cpus = self.getResource(offer.resources, 'cpus')
                mem = self.getResource(offer.resources, 'mem')
                if cpus < constants.TASK_CPU or mem < constants.TASK_MEM:
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
                    dict(name='cpus', type='SCALAR', scalar={'value': constants.TASK_CPU}),
                    dict(name='mem', type='SCALAR', scalar={'value': constants.TASK_MEM}),
                ]
                task.command.shell = True
                task.command.value = '/app/task.sh ' + self._message
                # task.command.arguments = [self._message]
                self._helper.addTaskToState(self._helper.initUpdateValue(task_id))
                #self._timers[task_id] = Timer(10.0,self.validateRunning(),kwargs={'taskid':task_id,'driver':driver,}).start()
                self._timers[task_id] = Timer(10.0,self.validateRunning,kwargs={'taskid' : task_id, 'driver': driver})
                self._timers[task_id].start()
                driver.launchTasks(offer.id, [task], filters)
            except Exception, e:
                logging.info(e)
                driver.declineOffer(offer.id, filters)

    def validateRunning(self, **kwargs):
        del self._timers[kwargs['taskid']]
        kwargs['driver'].reconcileTasks([dict(task_id={'value':kwargs['taskid']})])

    def getResource(self, res, name):
        for r in res:
            if r.name == name:
                return r.scalar.value
        return 0.0

    def statusUpdate(self, driver, update):
        logging.debug('Status update TID %s %s',
                      update.task_id.value,
                      update.state)
        if update.task_id.value in self._timers.keys():
            self._timers[update.task_id.value].cancel()
            del self._timers[update.task_id.value]
        if update.state in constants.TERMINAL_STATES:
            logging.info("terminal state for task: " + update.task_id.value)
            self._helper.removeTaskFromState(update.task_id.value)
            logging.info("tasks used = " + str(self._helper.getNumberOfTasks()) + " of " + self._max_tasks)
        else:
             self._helper.addTaskToState(update)   
            
    
def main(message, master, task_imp, max_tasks, redis_server):
    connection = redis.StrictRedis(host=redis_server, port=6379, db=0)
    framework = Dict()
    framework.user = getpass.getuser()
    framework.name = "MoralesMinimalFramework"
    framework.hostname = socket.gethostname()
    if connection.exists(":".join([framework.name,constants.REDIS_FW_ID])):
        logging.info("framework id already registered in redis")
        framework.id = dict(value=connection.get(":".join([framework.name,constants.REDIS_FW_ID])))

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

    while driver_thread.is_alive():
        time.sleep(1)
 
    logging.info("Disconnect from redis")
    keys = connection.scan(match = ":".join([framework.name,'*']))[1]
    logging.info(keys)
    entries = connection.delete(*keys)
    logging.info(entries)
    connection = None    

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) != 6:
        print("Usage: {} <message> <master> <task> <max_tasks> <redis_server>".format(sys.argv[0]))
        sys.exit(1)
    else:
        main(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5])        