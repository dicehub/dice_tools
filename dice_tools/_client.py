import sys
import socket
import msgpack
import argparse
import inspect
import traceback
import pprint
import _thread

from contextlib import contextmanager
from time import time
from select import select
from greenlet import greenlet
from ._wizard import wizard

__all__ = [
    'instantiate',
    'run',
    'app_settings',
    'browse_rdl',
    'notify',
    'signal',
    'switch',
    'app_log',
    'app'
    ]

app = None
sock = None
objects = {}
callbacks = {}

def dump_hook(obj):
    object_id = id(obj)
    if object_id in objects:
        return {'__object__': object_id}
    return obj

def load_hook(data):
    obj = data.get('__object__')
    if obj != None:
        return objects[obj]
    return data

def handle_result(call_id, value = None):
    count, callback = callbacks[call_id]
    if count == 1:
        del callbacks[call_id]
    else:
        callbacks[call_id] = (count - 1, callback)
    if isinstance(callback, greenlet):
        callback.switch(value)
    else:
        g = greenlet(task)
        g.switch(None, callback, value)

def handle_error(call_id, value = None):
    count, callback = callbacks[call_id]
    if count == 1:
        del callbacks[call_id]
    else:
        callbacks[call_id] = (count - 1, callback)
    if isinstance(callback, greenlet):
        callback.throw(Exception, 'call error')

def task(call_id, method, *args):
    try:
        result = method(*args)
        if call_id is not None:
            call(None, 'result', call_id, result)
    except greenlet.GreenletExit:
        raise
    except:
        traceback.print_exc()
        err = traceback.format_exc()
        call(None, 'error', call_id, err)

def call(obj, name, *args, **kwargs):
    callback = kwargs.get('callback')
    if callback:
        call_id = id(callback)
        info = callbacks.get(call_id)
        if info:
            callbacks[call_id] = (info[0] + 1, callback)
        else:
            callbacks[call_id] = (1, callback)
    else:
        call_id = None

    data = (id(obj) if obj is not None else None, name, call_id) + args
    message = msgpack.packb(data, default = dump_hook, use_bin_type=True)
    while message:
        message = message[sock.send(message):]

def call_ex(obj, name, *args):
    g_self = greenlet.getcurrent()
    call(obj, name, *args, callback = g_self)
    return g_self.parent.switch()

def instantiate(obj, type_name, *args):
    cls = type(obj)
    type_id = id(cls)
    if not cls.__dice_registered__:
        call(None, 'register', type_id, cls.__name__, cls.__dice_slots__,
            cls.__dice_signals__, cls.__dice_properties__)
        cls.__dice_registered__ = True
    object_id = id(obj)
    objects[object_id] = obj
    return call_ex(None, 'new', object_id, type_id, type_name, args)

def delete(obj):
    object_id = id(obj)
    call_ex(None, 'delete', object_id)
    del objects[object_id]

stdout_write_old = sys.stdout.write
stderr_write_old = sys.stderr.write

stdout_data = ''
stderr_data = ''

def w_stdout_write(data):
    global stdout_data
    if data:
        data = data.rsplit('\n', 1)
        if len(data) > 1:
            message = msgpack.packb(( None, 'stdout', None, stdout_data+data[0]), use_bin_type=True)
            while message:
                message = message[sock.send(message):]
            stdout_data = data[1]
        else:
            stdout_data += data[0]

def w_stderr_write(data):
    global stderr_data
    if data:
        data = data.rsplit('\n', 1)
        if len(data) > 1:
            message = msgpack.packb(( None, 'stderr', None, stderr_data+data[0]), use_bin_type=True)
            while message:
                message = message[sock.send(message):]
            stderr_data = data[1]
        else:
            stderr_data += data[0]

wizard.subscribe(w_stdout_write)
wizard.subscribe(w_stderr_write)

def stdout_write(data):
    stdout_write_old(data)
    if wizard.thread_ident != _thread.get_ident():
        wizard.w_stdout_write(data=data)
    else:
        w_stdout_write(data=data)

def stderr_write(data):
    stderr_write_old(data)
    if wizard.thread_ident != _thread.get_ident():
        wizard.w_stderr_write(data=data)
    else:
        w_stderr_write(data=data)

def app_settings():
    return call_ex(None, 'app_settings')

@contextmanager
def app_log(name):
    old_app_log = call_ex(None, 'app_log', name)
    try:
        yield
    finally:
        call_ex(None, 'app_log', old_app_log)

def browse_rdl(templates, entities):
    return call_ex(None, 'browse_rdl', templates, entities)

def notify(message=None, type="INFO", ttl=2.5, notify_id=None):
    params = dict(
            message = message,
            type = type,
            ttl = ttl,
            notify_id = notify_id
        )
    return call_ex(None, 'notify', params)

def signal(path, target=None):
    return call(None, 'signal', path, target)

def get_app_key(path):
    return call_ex(None, 'app_key', path)

def switch(timeout=0):
    g_self = greenlet.getcurrent()
    def f1():
        g_self.switch()
    def f2():
        wizard.timeout(f1, timeout)
    wizard.timeout(f2, 0)
    g_self.parent.switch()

parser = argparse.ArgumentParser()
parser.add_argument('--dice-addr', required = True, type=str)
parser.add_argument('--dice-port', required = True, type=int)
parser.add_argument('--dice-app-id', required = True, type=str)
parser.add_argument('--dice-workflow-dir', required = True, type=str)

def run():

    global sock

    reader, writer = socket.socketpair()
    reader.setblocking(0)
    writer.setblocking(0)

    def wake():
        writer.send(b'\x00')

    wizard.setup(wake)

    args, _ = parser.parse_known_args()

    sock = socket.socket()
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    sock.connect((args.dice_addr, args.dice_port))

    message = args.dice_app_id.encode('utf8') + b'\x00'
    while message:
        message = message[sock.send(message):]

    unpacker = msgpack.Unpacker(object_hook = load_hook, encoding='utf-8')

    sys.stdout.write = stdout_write
    sys.stderr.write = stderr_write

    def init_func():
        global app
        from ._types import Application
        Application.workflow_dir = args.dice_workflow_dir
        app = Application.__subclasses__()[0]()

    g = greenlet(task)
    g.switch(None, init_func)

    idle = 0

    def idle_func():
        nonlocal idle
        if idle == 1:
            idle = 2
        elif idle == 2:
            idle = -1
            wizard.w_idle()

    timeout = wizard.timeout(idle_func, 0.1, -1)

    while True:

        for f in wizard.get_timeouts():
            g = greenlet(task)
            g.switch(None, f)

        rfds, _, _ = select([reader, sock], [], [], wizard.get_delta())

        if rfds:
            idle = 0
        elif idle is 0:
             idle = 1

        if reader in rfds:
            try:
                while reader.recv(1024):
                    pass
            except BlockingIOError:
                pass
            for f in wizard.get_callbacks():
                g = greenlet(task)
                g.switch(None, f)

        if sock in rfds:
            try:
                sock.setblocking(0)
                while True:
                    buf = sock.recv(4096)
                    if not buf:
                        wizard.w_idle()
                        wizard.w_shutdown()
                        return                
                    unpacker.feed(buf)
            except BlockingIOError:
                sock.setblocking(1)

            for data in unpacker:
                if data[0] is None:
                    method = globals()['handle_' + data[1]]
                else:
                    if data[0] not in objects:
                        #send error
                        pass
                    try:
                        method = getattr(objects[data[0]], data[1])
                    except:
                        traceback.print_exc()
                        err = traceback.format_exc()
                        call(None, 'error', data[2], err)
                        continue
                g = greenlet(task)
                g.switch(data[2], method, *data[3:])