import eventlet
from oslo_log import log as logging


LOG = logging.getLogger(__name__)


class Flow(object):
    def __init__(self, id):
        self.parameter_list = []
        self.parameters_dict = {}
        self.next_task = 'noop'
        self.id = id
        self._must_stop = False

    def step(self):
        task_name = self.next_task

        LOG.debug("%s(%s) step(): task=%s, params=%s %s",
                  self.__class__.__name__,
                  self.id,
                  task_name,
                  self.parameter_list,
                  self.parameters_dict)

        function = getattr(self, task_name)
        parameter_list = self.parameter_list
        parameters_dict = self.parameters_dict
        result = function(*parameter_list, **parameters_dict)
        self.parameter_list = []
        self.parameters_dict = {}

        LOG.debug("%s(%s) step() task=%s done, result=%s.",
                  self.__class__.__name__,
                  self.id,
                  task_name,
                  str(result))
        return result

    def next(self, function, *parameter_list, **parameters_dict):
        self.parameter_list = parameter_list
        self.parameters_dict = parameters_dict
        self.next_task = function.__name__

    def run(self):
        eventlet.spawn_n(self._run)

    def _run(self):
        LOG.debug("%s(%s) run()", self.__class__.__name__, self.id)
        while not self._must_stop:
            result = self.step()
            if isinstance(result, int):
                LOG.debug("%s(%s) sleeping for %d seconds",
                          self.__class__.__name__, self.id, result)
                while result > 0 and not self._must_stop:
                    eventlet.sleep(1)
                    result -= 1
        LOG.debug("%s(%s) stopped.", self.__class__.__name__, self.id)

    def wait(self, seconds):
        return seconds

    def stop(self):
        self._must_stop = True

    def noop(self):
        LOG.debug("noop executed!")