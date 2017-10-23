# Standard Python modules
# =======================
from abc import ABCMeta
import inspect
import os
import sys
from functools import wraps, partial, cmp_to_key
import traceback
import pprint

# External modules
# ================

# DICE modules
# ============
from ._client import call, call_ex, instantiate, delete, app_log, socks
from ._wizard import wizard

__all__ = [
    'diceSlot',
    'diceSignal',
    'diceProperty',
    'DICEObject',
    'DICEObjectMeta',
    'Application',
    'ApplicationMeta',
    'diceTask',
    'diceSync',
    'diceCall'
]

class diceSlot:

    def __init__(self, *args, method=None, name=None, doc=None):
        self.__info = [(name, args)]
        if doc is None and method is not None:
            doc = method.__doc__
        self.__doc__ = doc
        if isinstance(method, diceSlot):
            self.__info += method.__info
            if doc is None:
                doc = method.__doc__
            method = method.__method
        self.__method = method

    def __call__(self, value):
        return type(self)(*self.__info[0][1], method=value, name=self.__info[0][0], doc=self.__doc__)

    def __get__(self, obj, tp = None):
        if obj is None:
            return self
        return self.__method.__get__(obj, tp)

    def _get(self, attr_name):
        result = []
        for name, args in self.__info:
            result.append({
                'signature': [v.__name__ 
                    if not isinstance(v, str) else v 
                    for v in args],
                'name': name or attr_name,
                'method_name': attr_name
                })
        return result

class diceSignal:
    """
    Instantiates signal suitable for use with Qt`s signal/slot system like
        pyqtSignal decorator. By default signal name matches instance name but
        could be overridden by "name" parameter.

    :param args: Signal arguments for passing data to connected slot.
    :param kwargs: Special parameters for slot. I.e. "name".
    """

    def __init__(self, *args, name=None, arguments=None):
        self.__name = name
        self.__arguments = arguments
        for v in args:
            if isinstance(v, (list, tuple)):
                self.__signatures = args
                break
        else:
            self.__signatures = (args,)

    @property
    def name(self):
        return self.__name

    def __get__(self, obj, tp = None):
        if obj is None:
            return self
        def f(*args):
            call(obj, '__dice_signal_emit__', self.__name, *args)
        return f

    def _get(self, attr_name):
        if not self.__name:
            self.__name = attr_name
        return {
            'signatures': [ 
                [i.__name__ if type == type(i) else i for i in v]
                for v in self.__signatures],
            'name': self.__name,
            'arguments': self.__arguments
        }

class diceProperty(property):
    """
    Defines property suitable for use with Qt`s property system. Syntax is
        like Python property syntax.

    :param tp: Property type. Could be Python types or strings with names
        of Qt types.
    :param fget: Function to get property data.
    :param fset: Function to set property data. I.e. "setter".
    :param notify: Signal that will be emitted.
    :param name: Property name seen by Qt. If omitted matches to property
        definition.
    """
    
    def __init__(self, tp, fget=None, fset=None, notify=None, name=None, doc=None):
        self.__type = tp
        self.__name = name
        self.__notify = notify
        self.__fget = fget
        self.__fset = fset
        if doc is None and fget is not None:
            doc = fget.__doc__
        self.__doc__ = doc

    def __call__(self, fget):
        return self.getter(fget)

    def getter(self, fget):
        return type(self)(self.__type, fget, self.__fset, self.__notify, self.__name, self.__doc__)

    def setter(self, fset):
        return type(self)(self.__type, self.__fget, fset, self.__notify, self.__name, self.__doc__)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if self.__fget is None:
            raise AttributeError("unreadable attribute")
        return self.__fget(obj)

    def __set__(self, obj, value):
        if self.__fset is None:
            raise AttributeError("can't set attribute")
        else:
            old_value = self.__fget(obj)
            self.__fset(obj, value)
            new_value = self.__fget(obj)
            if old_value != new_value:
                call(obj, '__dice_set_property__', self.__attr_name, new_value)

    def _send(self, obj):
        call(obj,
            '__dice_set_property__',
            self.__attr_name, self.__fget(obj),
            mode=1)

    def _sync(self, obj, value):
        if value:
            value = value[0]
            old_value = self.__fget(obj)
            self.__fset(obj, value)
            current = self.__fget(obj)
            if old_value != current:
                call(obj,
                    '__dice_set_property__',
                    self.__attr_name, current,
                    mode=2)
            if value != current:
                return (current,)
        else:
            return (self.__fget(obj),)

    def _get(self, attr_name):
        if not self.__name:
            self.__name = attr_name
        self.__attr_name = attr_name
        return {
            'type': self.__type.__name__ if type == type(self.__type) else self.__type,
            'name': self.__name,
            'attr_name': attr_name,
            'notify': self.__notify and self.__notify.name
        }

class CallProxy:

    __slots__ = 'object', 'real'

    def __init__(self, obj, real):
        self.object = obj
        self.real = real

    def __call__(self, *args, **kwargs):
        if 'callback' not in kwargs:
            return call_ex(self.object, self.real, *args)
        call(self.object, self.real, *args, **kwargs)

def diceCall(func = None, name=None, block=False):
    if func:
        if not name:
            name = func.__name__
        if block:
            def f(obj, *args, **kwargs):
                return call_ex(obj, name, *args)
        else:
            def f(obj, *args, **kwargs):
                call(obj, name, *args, **kwargs)
    else:
        def f(func, name = name, block=block):
            return diceCall(func, name, block)
    return f

class diceSync:

    def __init__(self, prefix, fget=None, fset=None, doc=None):
        self.prefix = prefix
        self.fget = fget
        self.fset = fset
        if doc is None and fget is not None:
            doc = fget.__doc__
        self.__doc__ = doc

    def __call__(self, fget):
        return self.getter(fget)

    def getter(self, fget):
        return type(self)(self.prefix, fget, self.fset, self.__doc__)

    def setter(self, fset):
        return type(self)(self.prefix, self.fget, fset, self.__doc__)

    def _sync(self, obj, path, value=()):
        if value:
            if self.fset is None:
                raise AttributeError("can't set value")
            elif self.fset(obj, path, value[0]):
                return None
        return (self.fget(obj, path),)

class DICEObjectMeta(ABCMeta):

    def __new__(mcls, name, bases, namespace):
        cls = super().__new__(mcls, name, bases, namespace)

        slots = []
        signals = []
        properties = []
        synchronizers = []

        for k, v in inspect.getmembers(cls):
            if type(v) == diceSignal:
                signals.append((k, v))
            elif type(v) == diceProperty:
                properties.append((k, v))
            elif type(v) == diceSlot:
                slots.append((k, v))
            elif type(v) == diceSync:
                synchronizers.append((v.prefix, v))

        cls.__dice_registered__ = False
        cls.__dice_slots__ = [i for k, v in slots for i in v._get(k)]
        cls.__dice_signals__ = [v._get(k) for k, v in signals]
        cls.__dice_properties__ = [v._get(k) for k, v in properties]
        cls.__dice_synchronizers__ = sorted(synchronizers, key=lambda x: len(x[0]))
        return cls

    def __call__(self, *args, **kwargs):
        obj = super().__call__(*args, **kwargs)
        if socks:
            obj.connect()
        return obj

class DICEObject(object, metaclass = DICEObjectMeta):

    __dice_initialized__ = False

    def __init__(self, base_type, **kwargs):
        instantiate(self, base_type)
        super().__init__(**kwargs)

    @diceCall(block=True)
    def connect(self):
        pass

    def connected(self):
        for info in self.__dice_properties__:
            getattr(self.__class__, info['attr_name'])._send(self)

    def __dice_sync_props__(self, props):
        result = {}
        for name, value in props.items():
            prop = getattr(self.__class__, name)
            current = prop._sync(self, value)
            if current:
                result[name] = current[0]
        return result

    def __dice_sync_value__(self, path, *value):
        for pre, s in self.__dice_synchronizers__:
            if path.startswith(pre):
                return s._sync(self, path[len(pre):], value)
        raise KeyError('path not found: %s'%path)
        
    def __getitem__(self, path):
        for pre, s in self.__dice_synchronizers__:
            if path.startswith(pre):
                return s.fget(self, path[len(pre):])
        raise KeyError('path not found: %s'%path)

    def __setitem__(self, path, value):
        for pre, s in self.__dice_synchronizers__:
            if path.startswith(pre):
                if s.fset is None:
                    raise AttributeError("can't set value")
                s.fset(self, path[len(pre):], value)
                return
        raise KeyError('path not found: %s'%path)

    def delete(self):
        delete(self)

def diceTask(name=None, prev=None, enabled=None):
    def wrap(f):
        f.__dicetask__ = dict(
            name = name or f.__name__,
            desc = f.__doc__,
            prev = prev,
            enabled = enabled)
        f.after = partial(diceTask, prev=f)
        return f
    return wrap

class ApplicationMeta(DICEObjectMeta):

    def __new__(mcls, name, bases, namespace):
        cls = super().__new__(mcls, name, bases, namespace)

        root_tasks = []
        next_tasks = {}
        for k, v in inspect.getmembers(cls):
            if hasattr(v, '__dicetask__'):
                prev = v.__dicetask__['prev']
                if prev:
                    next_tasks[prev] = v
                else:
                    root_tasks.append(v)
        tasks = []
        for v in root_tasks:
            tasks.append(v)
            while v in next_tasks:
                tasks.append(next_tasks[v])
                v = next_tasks[v]
        cls.__dice_tasks__ = tasks
        return cls

class Application(DICEObject, metaclass=ApplicationMeta):
    ''' This is basic class for application. Every DICE application
    class should inherit this class.

    :Attributes:
        :instance_name (str): Contains name for current application instance.
        :instance_status (str): String, representing current instance state.
        :config_path (str, readonly): This attribute contains path to current
            instance playground directory. This path should be used for storing
            and loading instance configuration, calculation result etc.
        :run_path (str): Path to current instance work directory
            (i.e. temporary)
    ''' 


    def __init__(self, instance_id, workflow_dir, progress, **kwargs):
        self.__instance_id = instance_id
        self.__progress = progress
        self.__workflow_dir = workflow_dir
        self.__running = False
        self.__stopped = False
        self.__console_locals = dict(app=self)
        super().__init__(base_type = 'BasicApp', **kwargs)


    def connected(self):
        super().connected()
        self.set_tasks(
            [m.__dicetask__['name'] for m in self.__dice_tasks__],
            mode=1)
        self.set_running(self.running, mode=1)

    @property
    def workflow_dir(self):
        return self.__workflow_dir

    @property
    def running(self):
        return self.__running

    @property
    def instance_id(self):
        return self.__instance_id

    @property
    def progress(self):
        return self.__progress

    def progress_changed(self, progress):
        self.__progress = progress

    def stop(self):
        self.__stopped = True

    def stopped(self):
        return self.__stopped

    def __set_runnning(self, running):
        self.__running = running
        self.set_running(running)

    def run(self, start, count):
        """
        Does all the calculations application designed for. Need to be
        implemented in application.

        :return bool: True on successful calculations.
        """

        self.__set_runnning(True)
        try:
            wizard.w_idle()
            start = max(start, 0)
            tasks_count = len(self.__dice_tasks__)
            if tasks_count == 0:
                return False
            if count:
                end = min(start + count, tasks_count)
            else:
                end = tasks_count 
            self.__stopped = False
            for idx in range(start, end):
                self.set_progress(idx)
                meth = self.__dice_tasks__[idx]
                if not self.running:
                    return False
                enabled = meth.__dicetask__['enabled']
                if enabled is not None and not enabled(self):
                    continue
                with app_log(meth.__dicetask__['name']):
                    if meth.__dicetask__['desc']:
                        self.log(meth.__dicetask__['desc'])
                    try:
                        res = meth(self)
                        if not res:
                            return False
                    except:
                        self.log(traceback.format_exc())
                        raise
            if end == tasks_count:
                self.set_progress(-1)
            else:
                self.set_progress(end)
            return True
        finally:
            self.__set_runnning(False)

    def input_changed(self, input_data):
        pass

    def internal_input_changed(self, input_data):
        pass

    def behaviour_changed(self, behaviour):
        pass

    def input_types_changed(self, input_types):
        pass

    def internal_input_types_changed(self, input_types):
        pass

    def output_types_changed(self, output_types):
        pass

    def internal_output_types_changed(self, output_types):
        pass


    @diceCall
    def alert(self):
        pass

    @diceCall
    def debug(self):
        pass

    @diceCall
    def log(self):
        pass

    @diceCall
    def set_tasks(self, tasks):
        pass

    @diceCall
    def set_running(self, running):
        pass

    @diceCall(block=True)
    def run_internal(self):
        pass

    @diceCall(block=True)
    def set_behaviour(self, behaviour):
        pass

    @diceCall(block=True)
    def set_input_types(self, inputs):
        pass

    @diceCall(block=True)
    def set_output_types(self, outputs):
        pass

    @diceCall(block=True)
    def set_internal_input_types(self, inputs):
        pass

    @diceCall(block=True)
    def set_internal_output_types(self, outputs):
        pass

    @diceCall(block=True)
    def set_progress(self, progress):
        pass

    @diceCall(block=True)
    def set_output(self, type_name, value):
        pass

    @diceCall(block=True)
    def set_internal_output(self, type_name, value):
        pass

    def config_path(self, *args, relative=False):
        """
        Returns application`s config_dir under workflow_dir joined with args.

        :param args: Final part of returned path. See os.path.join.
        :return: Result path.
        """
        return self.workflow_path('config', self.instance_id, *args, relative = relative)

    def run_path(self, *args, relative=False):
        """
            Returns application`s run_dir under workflow_dir joined with args.

            :param args: Final part of returned path. See os.path.join.
            :return: Result path.
        """
        return self.workflow_path('run', self.instance_id, *args, relative = relative)

    def workflow_path(self, *args, relative=False):
        """
            Returns application`s workflow_dir joined with args.

            :param args: Final part of returned path. See os.path.join.
            :return: Result path.
        """
        if relative:
            return os.path.join(*args)
        else:
            return os.path.join(self.workflow_dir, *args)

    def execute_text(self, text, locals_dict=None):
        if locals_dict is None:
            locals_dict = self.__console_locals

        print('>>> ' + text)
        try:
            try:
                try:
                    res = eval(text, {}, locals_dict)
                    if res is not None:
                        pprint.pprint(res, width=200)
                except SyntaxError:
                    tb = sys.exc_info()[2]
                    if tb.tb_next is None:
                        exec(text, {}, locals_dict)
                    else:
                        raise
            except NameError as e:
                tb = sys.exc_info()[2]
                if tb.tb_next and tb.tb_next.tb_next is None:
                    print("Error: %s\n"%e.args[0])
                else:
                    raise
        except:
            exc = traceback.format_exc(chain=False).split('\n')
            print("Error:\n%s\n"%'\n'.join(exc[:1]+exc[3:]))
