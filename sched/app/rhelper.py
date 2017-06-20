from addict import Dict
import constants
import logging

class Helper():

    def __init__(self,redis,fwk_name):
        self._redis = redis
        self._fwk_name = fwk_name

    def register(self, fwkid, master_info):
        logging.info(fwkid)
        self._redis.set(":".join([self._fwk_name, constants.REDIS_FW_ID]), fwkid)
        logging.info(master_info)
        self._redis.hmset(":".join([self._fwk_name, constants.REDIS_MASTER_INFO]),master_info)


    def reregister(self, master_info):    
        self._redis.hmset(":".join([self._fwk_name, constants.REDIS_MASTER_INFO]),master_info)
    
    def getTasksSet(self,setName):
        tasks = self._redis.hget(self._fwk_name,setName)
        if tasks == None:
            res = set()
        else:
            res = eval(tasks)
        return res

    def initUpdateValue(self,taskId):
        update=Dict()
        update.executor_id= dict(value='')
        update.uuid=''
        update.task_id=dict(value=taskId)
        update.container_status=dict()
        update.source=''
        update.state='TASK_STAGING'
        update.agent_id=dict(value='')
        return update

    def getTaskState(self,update):
        task=Dict()
        logging.info(update)
        task[constants.SOURCE_KEY_TAG] = update.source
        task[constants.STATE_KEY_TAG] = update.state
        task[constants.AGENT_KEY_TAG] = update.agent_id['value']
        return task

    '''
    Method that checks if the scheduler can manage another task, checking if the number of tasks isn't greather than
    the maximum number of tasks parameter
    Parameters
    ----------
    maxTasks (string) : maximum number of allowed tasks
    '''
    def checkTask(self,maxTasks):
        count = self.getNumberOfTasks()
        logging.info("CHECK TASK: " + str(count) + " "+maxTasks)
        if count >= int(maxTasks):
            logging.info("Reached maximum number of tasks")
            raise Exception('maximum number of tasks')
        else:
            logging.info("number tasks used = " + str(count) + " of " + maxTasks)


    '''
    Method that adds a task to framework (key) state 
    Parameters
    ----------
    updateTask(Dictionary): information about task that contains:
        taskId (string): identifier of the task
        container(string)
        source (string)
        status (string): current status of the task (running,lost,...)
        agent (string)
    '''
    def addTaskToState(self,updateTask):
        task=self.getTaskState(updateTask)
        logging.info("add task")
        logging.info(task)
        self._redis.hmset(":".join([self._fwk_name, constants.REDIS_TASKS_SET,updateTask['task_id']['value']]), task)
    '''
    Method that removes a task from framework (key) state
    Parameters
    ----------
    taskId (string): identifier of the task
    '''
    def removeTaskFromState(self,taskId):
        self._redis.delete(":".join([self._fwk_name, constants.REDIS_TASKS_SET,taskId]))


    '''
    Method that returns the number of tasks managed by one framework(key)
    '''
    def getNumberOfTasks(self):
#        return len(self._redis.hkeys(self._fwk_name))//4
        actualTasks = self._redis.scan(match = ":".join([self._fwk_name, constants.REDIS_TASKS_SET,'*']))[1]
        return len(actualTasks)
