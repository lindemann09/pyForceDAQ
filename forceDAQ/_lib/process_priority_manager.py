#!/usr/bin/env python3

import gc
import sys
import psutil
import logging

_REALTIME_PRIORITY_CLASS = -18
_HIGH_PRIORITY_CLASS = -10

NORMAL_PRIORITY = 'normal'
HIGH_PRIORITY = 'high'
REALTIME_PRIORITY = 'real_time'

class ProcessPriorityManager(object):

    platform = sys.platform
    pybits = 32 + int(sys.maxsize > 2 ** 32) * 32
    parent_process_id = psutil.Process().pid
    _normal_nice_value = psutil.Process().nice() # usied on Linux

    def __init__(self):
        self._subprocs = []

    def add_subprocess(self, process):
        """add process or list of processes"""

        if isinstance(process, (list, tuple)):
            for x in process:
                self.add_subprocess(x)
            return

        try:
            pid = process.pid
            self._subprocs.append(process)
        except:
            logging.warning("Can't add process: {}".format(process))

    def get_subprocess_priorities(self):
        """returns list with priorities"""

        rtn = []
        for p in self._subprocs:
            if p.pid is not None:
                rtn.append(ProcessPriorityManager._get_priority(p.pid))
            else:
                rtn.append(None)

        return rtn

    def set_subprocess_priorities(self, level, disable_gc=False):

        rtn = []
        for p in self._subprocs:
            if p.pid is not None:
                rtn.append(ProcessPriorityManager._set_priority(level=level,
                                                     process_id=p.pid,
                                                     disable_gc=disable_gc))
            else:
                rtn.append(False)

        return rtn


    @staticmethod
    def get_main_priority():
        """
            returning main process priority, if subprocess_id=None
            Priority: 'normal', 'high', or 'realtime'
        """
        pid = ProcessPriorityManager.parent_process_id
        return ProcessPriorityManager._get_priority(pid)

    @staticmethod
    def set_main_priority(level, disable_gc=False):
        """
            changing main process, if subprocess_id=None
        """

        pid = ProcessPriorityManager.parent_process_id
        return ProcessPriorityManager._set_priority(level=level,
                                                    process_id=pid,
                                                    disable_gc=disable_gc)

    @staticmethod
    def _get_priority(process_id):
        """
            returning main process priority, if subprocess_id=None
            Priority: 'normal', 'high', or 'realtime'
        """

        try:
            process = psutil.Process(process_id)
        except:
            return None

        proc_priority = process.nice()
        if ProcessPriorityManager.platform == 'win32':
            if proc_priority == psutil.HIGH_PRIORITY_CLASS:
                return HIGH_PRIORITY
            elif proc_priority == psutil.REALTIME_PRIORITY_CLASS:
                return REALTIME_PRIORITY

        else:
            if proc_priority <= _REALTIME_PRIORITY_CLASS:
                return REALTIME_PRIORITY
            elif proc_priority <= _HIGH_PRIORITY_CLASS:
                return HIGH_PRIORITY

        return NORMAL_PRIORITY


    @staticmethod
    def _set_priority(level, process_id, disable_gc):

        try:
            process = psutil.Process(process_id)
        except:
            return False

        nice_val = ProcessPriorityManager._normal_nice_value
        if level == NORMAL_PRIORITY:
            disable_gc = False
        elif level == HIGH_PRIORITY:
            nice_val = _HIGH_PRIORITY_CLASS
            if ProcessPriorityManager.platform == 'win32':
                nice_val = psutil.HIGH_PRIORITY_CLASS
        elif level == REALTIME_PRIORITY:
            nice_val = _REALTIME_PRIORITY_CLASS
            if ProcessPriorityManager.platform == 'win32':
                nice_val = psutil.REALTIME_PRIORITY_CLASS

        try:
            process.nice(nice_val)
            if disable_gc:
                gc.disable()
            else:
                gc.enable()
        except psutil.AccessDenied:
            logging.warning('Could not set process {} priority '
                      'to {}'.format(process.pid, nice_val))

        return True


#    def getProcessAffinities(): TODO?
#
#       curproc_affinity = SubProcessPriorityManager.current_process.cpu_affinity()
#        return curproc_affinity

#    @staticmethod
#    def setProcessAffinities(experimentProcessorList, ioHubProcessorList):
#        SubProcessPriorityManager.current_process.cpu_affinity(experimentProcessorList)

