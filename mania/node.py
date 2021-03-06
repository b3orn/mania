# -*- coding: utf-8 -*-

'''
   mania.node
   ~~~~~~~~~~

   :copyright: (c) 2014 by Björn Schulz.
   :license: MIT, see LICENSE for more details.
'''

from __future__ import absolute_import, division
import sys
import logging
import io
import time
import os.path
import multiprocessing
import threading
import importlib
import pkgutil
import Queue as queue
import operator
import traceback
import mania.builtins
import mania.instructions
import mania.types
from mania.frame import Frame, Scope, Stack


logger = logging.getLogger(__name__)


DEFAULT_TICK_LIMIT = 1024


RUNNING = 'running'
EXITING = 'exiting'
WAITING_FOR_MESSAGE = 'waiting-for-message'
WAITING_FOR_MODULE = 'waiting-for-module'


class Schedule(Exception):
    pass


class LoadingDeferred(Exception):
    pass


class Node(object):

    def __init__(self, tick_limit, scheduler_count, paths):
        self.tick_limit = tick_limit
        self.scheduler_count = scheduler_count
        self.paths = paths
        self.schedulers = []
        self.registered_modules = {}
        self.loaded_modules = {}
        self._next_id = 0
        self.id_lock = threading.Lock()
        self.spawn_lock = threading.Lock()
        self.load_lock = threading.Lock()
        self.started = threading.Lock()
        self.scheduled_processes = []

    @property
    def next_pid(self):
        with self.id_lock:
            pid = self._next_id

            self._next_id += 1

        return pid

    def start(self):
        try:
            self.init_schedulers()

            for scheduler in self.schedulers:
                scheduler.start()

            self.init_modules()

            self.started.acquire()

            for process in self.scheduled_processes:
                self._spawn_process(process)

            self.scheduled_processes = []

            self.run()

        finally:
            self.stop()
            self.started.release()

            logger.info('Node stopped')

    def stop(self):
        for scheduler in self.schedulers:
            scheduler.stopping.acquire()

    def init_schedulers(self):
        self.schedulers = []

        for i in xrange(self.scheduler_count):
            self.schedulers.append(Scheduler(self, self.tick_limit))

    def init_modules(self):
        builtins = pkgutil.iter_modules(
            [os.path.join(os.path.dirname(__file__), 'builtins')],
            prefix='mania.builtins.'
        )

        for loader, name, _ in builtins:
            module = importlib.import_module(name)

            for key in dir(module):
                value = getattr(module, key, None)

                if isinstance(value, type) and issubclass(value, mania.types.NativeModule):
                    library = value()

                    self.loaded_modules[library.name] = library

        boot = self.loaded_modules[mania.types.Symbol('mania:boot')]

        for path in self.paths:
            for root, directories, filenames in os.walk(path):
                for filename in filenames:
                    if os.path.splitext(filename)[1] != '.bam':
                        continue

                    with open(os.path.join(root, filename), 'rb') as stream:
                        module = Module.load(stream)

                        self.spawn_process(
                            module.code(module.entry_point),
                            Scope(parent=boot.scope)
                        )

    def run(self):
        while any(s.alive and (s.processes or s.new_processes) for s in self.schedulers):
            for scheduler in self.schedulers:
                if scheduler.alive:
                    scheduler.join(0.1)

    def spawn_process(self, code, scope=None):
        with self.spawn_lock:
            process = Process(None, self.next_pid, code, scope)

            try:
                if self.started.acquire(False):
                    release = True

                    self.scheduled_processes.append(process)

                else:
                    release = False

                    self._spawn_process(process)

            finally:
                if release:
                    self.started.release()

        return process

    def _spawn_process(self, process):
        scheduler = sorted([
            (len(s.registered_processes), s)
            for s in self.schedulers
        ])[0][1]

        scheduler.spawn_process(process)

    def kill_process(self, pid):
        for scheduler in self.schedulers:
            try:
                scheduler.kill_process(pid)

            except KeyError:
                pass

    def load_module(self, name):
        with self.load_lock:
            if name in self.loaded_modules:
                if name in self.registered_modules:
                    del self.registered_modules[name]

                return self.loaded_modules[name]

            elif name in self.registered_modules:
                module = self.registered_modules[name]
                default = self.loaded_modules[mania.types.Symbol('mania')]

                self.spawn_process(
                    code=module.code(module.entry_point),
                    scope=Scope(parent=default.scope)
                )

                raise LoadingDeferred()

            raise ImportError('Module {0!r} not found'.format(name.value))


class Scheduler(object):

    def __init__(self, node, tick_limit):
        self.node = node
        self.tick_limit = tick_limit
        self.thread = threading.Thread(target=self.run)
        self.processes = []
        self.new_processes = []
        self.registered_processes = {}
        self.stopping = threading.Lock()
        self.spawn_lock = threading.Lock()

    @property
    def next_pid(self):
        return self.node.next_id

    @property
    def alive(self):
        return self.thread.is_alive()

    def join(self, timeout):
        self.thread.join(timeout)

    def start(self):
        self.thread.start()

    def run(self):
        while self.stopping.acquire(False):
            self.stopping.release()

            with self.spawn_lock:
                scheduled_processes = self.processes + self.new_processes
                self.new_processes = []

            self.processes = []

            for process in scheduled_processes:
                if process.status == RUNNING:
                    self.processes.append(process)

                    try:
                        ticks = process.run(self.tick_limit)

                        process.priority += ticks / self.tick_limit

                    except Exception as exception:
                        ex_type, _, trace = sys.exc_info()

                        process.status = EXITING

                        logger.info('Process {0} stopped with unhandled exception {1} {2}'.format(
                            process.id,
                            exception,
                            ''.join(traceback.format_tb(trace))
                        ))

                elif process.status == WAITING_FOR_MESSAGE:
                    self.processes.append(process)

                    if not process.queue.empty():
                        process.status = RUNNING

                elif process.status == WAITING_FOR_MODULE:
                    self.processes.append(process)

                    if process.waiting_for in self.node.loaded_modules:
                        process.status = RUNNING

                elif process.status == EXITING:
                    if process.id in self.registered_processes:
                        del self.registered_processes[process.id]

                    logger.info('Process {0} stopped'.format(process.id))

            self.processes.sort(key=operator.attrgetter('priority'))

    def spawn_process(self, process):
        with self.spawn_lock:
            process.scheduler = self

            self.registered_processes[process.id] = process

            self.new_processes.append(process)

        return process

    def kill_process(self, pid):
        self.registered_processes[pid].kill()


class Process(object):

    def __init__(self, scheduler, id, code, scope):
        self.scheduler = scheduler
        self.id = id
        self.priority = 0
        self.status = RUNNING
        self.kill_status = None
        self.queue = queue.Queue()
        self.waiting_for = None
        self.vm = VM(self, code, scope)
        self.status_lock = threading.Lock()
        self.kill_lock = threading.Lock()

    def kill(self):
        try:
            if self.status_lock.acquire(False):
                release = True

                self.status = EXITING

            else:
                release = False

                with self.kill_lock:
                    self.kill_status = EXITING

        finally:
            if release:
                self.status_lock.release()

    def run(self, ticks):
        with self.status_lock:
            if self.status == RUNNING:
                ticks = self.vm.run(ticks)

            if self.kill_status is not None:
                self.status = EXITING

            return ticks


class VM(object):

    def __init__(self, process, code, scope):
        self.process = process
        self.frame = Frame(code=code, scope=scope)
        self.switches = 0

    def tick(self):
        instruction = self.frame.code[self.frame.position]

        self.frame.position += 1

        frame = self.frame

        instruction.eval(self)

        limit = self.frame.code.entry_point + self.frame.code.size

        if self.frame.position >= limit:
            self.switches += 1

            self.restore()

            return

        if self.frame is not frame:
            self.switches += 1

            last = self.frame.code[limit - 1]

            if frame.position < frame.code.entry_point + frame.code.size:
                next = frame.code[frame.position]

                if isinstance(next, mania.instructions.Return):
                    if isinstance(last, mania.instructions.Return):
                        self.frame.parent = frame.parent

                    elif isinstance(last, mania.instructions.Restore):
                        for i in xrange(self.frame.code.entry_point, limit):
                            instruction = self.frame.code[i]

                            if isinstance(instruction, mania.instructions.Restore):
                                self.frame.code[i] = next

                elif isinstance(next, mania.instructions.Restore):
                    if isinstance(last, mania.instructions.Restore):
                        self.frame.parent = frame.parent

            else:
                if not isinstance(last, mania.instructions.Return):
                    self.frame.parent = frame.parent

    def run(self, ticks):
        for tick in xrange(ticks):
            try:
                self.tick()

            except Schedule:
                logger.info('schedule at tick {0}/{1}'.format(
                    tick + 1,
                    ticks
                ))

                break

        return ticks - (tick + 1)

    def restore(self, frame=None):
        if frame is None:
            frame = self.frame.parent
        
        if frame:
            self.frame = frame

        else:
            self.process.kill()

            raise Schedule()

    def throw(self, name, message=None):
        raise Exception(name)
