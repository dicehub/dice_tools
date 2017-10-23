import _thread

from types import MethodType, FunctionType
from inspect import signature
from weakref import ref, WeakKeyDictionary, WeakSet, WeakMethod
from heapq import heappush, heappop
from time import time
from collections import Counter
from queue import Queue, Empty


__all__ = ['wizard']


class _Wizard:
    
    class _Timeout:

        __slots__ = 'sub', 'delay', 'repeats', 'ts'

        def __init__(self, sub, delay, repeats):
            self.sub = ref(sub, self.remove)
            self.delay = delay
            self.repeats = repeats
            self.reset()

        def reset(self):
            self.ts = self.delay + time()

        def remove(self, *args):
            self.repeats = 0
            for i, v in enumerate(wizard.timeouts):
                if v[1] == self:
                    del wizard.timeouts[i]
                    return

        def __lt__(self, other):
            return self.ts < other.ts

    class _Subscriber(ref):

        __slots__ = '__weakref__'

        def __eq__(self, other):
            if isinstance(other, _Wizard._Subscriber):
                return ref.__eq__(self, other)
            return False

        __hash__ = ref.__hash__

    def __init__(self):
        self.subs = WeakKeyDictionary()
        self.refs = WeakKeyDictionary()
        self.objs = {}
        self.methods = {}

        self.timeouts = []
        self.callbacks = Queue()
        self.thread_ident = None
        self.wake = lambda: None

    def setup(self, wake):
        self.wake = wake
        self.thread_ident = _thread.get_ident()
        self.wake()

    def get_delta(self):
        if self.timeouts:
            return max(0, self.timeouts[0][0] - time())
        return None

    def get_timeouts(self):
        result = []
        while self.timeouts:
            ts, timeout = self.timeouts[0]
            delta = ts - time()
            if delta <= 0:
                self.timeouts.pop(0)
                if timeout.ts == ts:
                    def f(timeout=timeout):
                        timeout.repeats -= 1
                        sub = timeout.sub()()
                        if sub:
                            sub()
                        if timeout.repeats != 0:
                            timeout.reset()
                            heappush(self.timeouts, (timeout.ts, timeout))
                    result.append(f)
                else:
                    heappush(self.timeouts, (timeout.ts, timeout))
            else:
                break
        return result

    def get_callbacks(self):
        result = []
        try:
            while True:
                method, args, kwargs = self.callbacks.get(False)
                def f():
                    self.__getattr__(method)(*args, **kwargs)
                result.append(f)
        except Empty:
            return result

    def timeout(self, subscriber, delay=0, repeats=1):
        if isinstance(subscriber, MethodType):
            parent = subscriber.__self__
            subscriber = WeakMethod(subscriber)
        else:
            if isinstance(subscriber, FunctionType):
                parent = subscriber
                subscriber = _Wizard._Subscriber(subscriber)
            else:
                raise ValueError('Timeout subscriber must be callable.')

        subscriber = self.subs.setdefault(parent, dict()).setdefault(
            subscriber, subscriber)
        timeout = _Wizard._Timeout(subscriber, delay, repeats)
        heappush(self.timeouts, (timeout.ts, timeout))
        return timeout

    def remove_timeout(self, timeout):
        timeout.remove()

    _undefined = object()

    def subscribe(self, *args, **kwargs):
        subscriber, *args = args
        if type(subscriber) == str or subscriber is None:
            method = subscriber
            subscriber, *args = args
        else:
            method = _Wizard._undefined

        if args:
            key, item = None, args[0]
        else:
            for key, item in kwargs.items():
                break
            else:
                key, item = None, _Wizard._undefined

        if isinstance(subscriber, MethodType):
            is_callable = True
            parent = subscriber.__self__
            subscriber = WeakMethod(subscriber)
        else:
            if isinstance(subscriber, FunctionType):
                is_callable = True
            else:
                is_callable = False
            parent = subscriber
            subscriber = _Wizard._Subscriber(subscriber)

        subscriber = self.subs.setdefault(parent, dict()).setdefault(
            subscriber, subscriber)

        if is_callable:
            if method is _Wizard._undefined:
                method = subscriber().__name__
            if isinstance(key, str):
                for i, v in enumerate(signature(subscriber()).parameters):
                    if v == key:
                        key = i
        elif key is not None:
            raise ValueError("Can't create subscribtion, key argument allowed for callable only")

        if method not in (None, _Wizard._undefined):
            subs, refs, objs, idx = self.methods.setdefault(method, 
                (WeakSet(), WeakKeyDictionary(), {}, {}))
            if item is _Wizard._undefined:
                subs.add(subscriber)
            elif key is not None:
                refs, objs = idx.setdefault(key, (WeakKeyDictionary(), {}))
        elif item is _Wizard._undefined:
            raise ValueError("Can't create subscribtion, 'item' argument is required")
        else:
            refs, objs = self.refs, self.objs

        try:
            refs.setdefault(item, WeakSet()).add(subscriber)
        except TypeError:
            objs.setdefault(item, WeakSet()).add(subscriber)

    def unsubscribe(self, *args, **kwargs):
        subscriber, *args = args
        if type(subscriber) == str or subscriber is None:
            method = subscriber
            subscriber, *args = args
        else:
            method = _Wizard._undefined

        if args:
            key, item = None, args[0]
        else:
            for key, item in kwargs.items():
                break
            else:
                key, item = None, _Wizard._undefined

        if isinstance(subscriber, MethodType):
            is_callable = True
            parent = subscriber.__self__
            subscriber = WeakMethod(subscriber)
        else:
            if isinstance(subscriber, FunctionType):
                is_callable = True
            else:
                is_callable = False
            parent = subscriber
            subscriber = _Wizard._Subscriber(subscriber)

        if parent in self.subs:
            if item is _Wizard._undefined and method is _Wizard._undefined:
                if subscriber() is parent:
                    del self.subs[parent]
                elif subscriber in self.subs[parent]:
                    del self.subs[parent][subscriber]

            elif subscriber in self.subs[parent]:

                if item is not _Wizard._undefined:
                    if is_callable:
                        if method is _Wizard._undefined:
                            method = subscriber().__name__
                        if isinstance(key, str):
                            for i, v in enumerate(signature(subscriber()).parameters):
                                if v == key:
                                    key = i
                                    
                if method not in (None, _Wizard._undefined):
                    if method in self.methods:
                        subs, refs, objs, idx = self.methods[method]
                        if item is _Wizard._undefined:
                            subs.discard(subscriber)
                        if key in idx:
                            refs, objs = idx[key]
                else:
                    refs, objs = self.refs, self.objs

                try:
                    subs = refs.get(item)
                except TypeError:
                    subs = objs.get(item)
                if subs:
                    subs.discard(subscriber)

    def __getattr__(self, method):

        if self.thread_ident != _thread.get_ident():
            def f(*args, **kwargs):
                self.callbacks.put((method, args, kwargs))
                self.wake()
            return f

        def f(*args, **kwargs):

            if method in self.methods:
                method_data = self.methods[method]
                subs = list(method_data[0])
            else:
                method_data = None
                subs = []

            def collect(v, refs, objs):
                nonlocal subs
                try:
                    subs += list(objs.get(v, ()))
                    subs += list(refs.get(v, ()))
                except TypeError:
                    pass

            for i, v in enumerate(args):
                if method_data:
                    collect(v, method_data[1], method_data[2])
                    if i in method_data[3]:
                        refs, objs = method_data[3][i]
                        collect(v, refs, objs)
                collect(v, self.refs, self.objs)

            for s in subs:
                v = getattr(s(), method, s())
                if callable(v):
                    v(*args, **kwargs)

        return f

    def __repr__(self):
        return repr(self.info())

    def info(self):
        """
        Returns current subscriptions where keys are subscribers and values are
        list of targets

        :return dict: Dictionary with subscriptions
        """
        info = {}
        for v, subs in self.refs.items():
            for s in subs:
                info.setdefault(s, set()).add(v)
        for v, subs in self.objs.items():
            for s in subs:
                info.setdefault(s, set()).add(v)
        return {k: list(v) for k, v in info.items()}


wizard = _Wizard()
