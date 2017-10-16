import sys
import socket
import msgpack
import argparse
import inspect
import traceback
import pprint
import _thread
import traceback

from contextlib import contextmanager
from time import time
from select import select
from ._wizard import wizard

__all__ = [
    'instantiate',
    'run',
    'app_settings',
    'browse_rdl',
    'notify',
    'signal',
    'process_messages',
    'app_log',
    'app',
    'call',
    'call_ex',
    'connect',
    'socks'
    ]

app = None
socks = []
packs = {}
objects = {}
callbacks = {}
types = {}
current_socket = None
reader = None
log_name = ''
settings = {}
master_sock = None

def dump_hook(obj):
    object_id = id(obj)
    if object_id in objects:
        return {'__object__': object_id}
    return obj

def load_hook(data):
    obj = data.get('__object__')
    if obj != None:
        return objects[obj][0]
    return data

def handle_result(call_id, value = None):
    count, callback = callbacks[call_id]
    if count == 1:
        del callbacks[call_id]
    else:
        callbacks[call_id] = (count - 1, callback)
    callback(value)

def handle_error(call_id, value = None):
    count, callback = callbacks[call_id]
    if count == 1:
        del callbacks[call_id]
    else:
        callbacks[call_id] = (count - 1, callback)
    callback(Exception('DICE call error'))

def handle_settigs(value):
    global settings
    settings = value

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
    send(message, kwargs.get('mode', 0))

def call_ex(obj, name, *args):
    result = None
    finished = False
    def callback(x):
        nonlocal finished
        nonlocal result
        finished = True
        result = x
    call(obj, name, *args, callback=callback, mode=3)
    wait(lambda: finished)
    if isinstance(result, Exception):
        raise result
    return result

def instantiate(obj, type_name):
    object_id = id(obj)
    objects[object_id] = (obj, type_name)
    if socks:
        register_type(obj)
        create_object(obj, type_name)

def register_type(obj):
    cls = type(obj)
    type_id = id(cls)
    for s in socks:
        if cls not in types[s]:
            call(None, 'register', type_id, cls.__name__, cls.__dice_slots__,
                cls.__dice_signals__, cls.__dice_properties__)
            types[s].add(cls)

def create_object(obj, type_name, mode=0):
    object_id = id(obj)
    cls = type(obj)
    type_id = id(cls)
    call(None, 'new', object_id, type_id, type_name, mode=mode)

def delete(obj):
    object_id = id(obj)
    call(None, 'delete', object_id)
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
            send(message)
            stdout_data = data[1]
        else:
            stdout_data += data[0]

def w_stderr_write(data):
    global stderr_data
    if data:
        data = data.rsplit('\n', 1)
        if len(data) > 1:
            message = msgpack.packb(( None, 'stderr', None, stderr_data+data[0]), use_bin_type=True)
            send(message)
            stderr_data = data[1]
        else:
            stderr_data += data[0]

def send(message, mode=0):

    ss = {s: 0 for s in socks

        if ((mode == 1 and s == current_socket)
            or (mode == 2 and s != current_socket)
            or (mode == 3 and s == master_sock)
            or not mode)
    }

    while ss:
        for s in list(ss):
            ss[s] += s.send(message[ss[s]:])
            if ss[s] == len(message):
                del ss[s]

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
    global log_name
    old_app_log = log_name
    log_name = name
    call(None, 'app_log', name)
    try:
        yield
    finally:
        log_name = old_app_log
        call(None, 'app_log', old_app_log)

def browse_rdl(templates, entities):
    return call_ex(None, 'browse_rdl', templates, entities)

def notify(message=None, type="INFO", ttl=2.5, notify_id=None):
    params = dict(
            message = message,
            type = type,
            ttl = ttl,
            notify_id = notify_id
        )
    return call(None, 'notify', params)

def signal(path, target=None):
    return call(None, 'signal', path, target)

parser = argparse.ArgumentParser()
parser.add_argument('--dice-addr', required = True, type=str)
parser.add_argument('--dice-port', required = True, type=int)
parser.add_argument('--dice-progress', required = True, type=int)
parser.add_argument('--dice-instance-id', required = True, type=str)
parser.add_argument('--dice-workflow-dir', required = True, type=str)

def connect(addr, port):
    global master_sock
    global current_socket

    sock = socket.socket()
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.connect((addr, port))
    message = app.instance_id.encode('utf8') + b'\x00'
    while message:
        message = message[sock.send(message):]
    socks.append(sock)
    packs[sock] = msgpack.Unpacker(object_hook = load_hook, encoding='utf-8')
    types[sock] = set()

    with set_socket(sock):
        if master_sock is None:
            master_sock = sock
        for (obj, type_name) in objects.values():
            register_type(obj)
        for (obj, type_name) in objects.values():
            create_object(obj, type_name, mode=1)
        for (obj, type_name) in objects.values():
            obj.connect()
        call(None, 'ready', app, mode=1)

def disconnect(s):
    socks.remove(s)
    del packs[s]
    del types[s]

def wait(stop):
    while not stop():
        process_messages()

@contextmanager
def set_socket(sock):
    global current_socket
    old_sock = current_socket
    current_socket = sock
    try:
        yield
    finally:
        current_socket = old_sock


def process_messages():
    global reader
    global idle

    for f in wizard.get_timeouts():
        f()

    rdfs, _, _ = select([reader] + socks, [], [], wizard.get_delta())

    if rdfs:
        idle = 0
    elif rdfs is 0:
        idle = 1

    current = []

    for s in rdfs:
        if s == reader:
            try:
                while s.recv(1024):
                    pass
            except BlockingIOError:
                pass
            for f in wizard.get_callbacks():
                f()
        else:
            p = packs[s]
            try:
                s.setblocking(0)
                while True:
                    buf = s.recv(4096)
                    if not buf:
                        disconnect(s)
                        s = None
                        break
                    p.feed(buf)
            except BlockingIOError:
                s.setblocking(1)

            current.append((s, p))

    for s, p in current:
        with set_socket(s):
            for data in p:
                obj_id, method_name, call_id, *method_args = data

                if obj_id is None:
                    method = globals()['handle_' + data[1]]
                else:
                    if obj_id not in objects:
                        #send error
                        pass
                    try:
                        method = getattr(objects[obj_id][0], method_name)
                    except:
                        traceback.print_exc()
                        err = traceback.format_exc()
                        call(None, 'error', call_id, err)
                        continue

                try:
                    result = method(*method_args)
                    if call_id is not None:
                        call(None, 'result', call_id, result)
                except:
                    traceback.print_exc()
                    err = traceback.format_exc()
                    call(None, 'error', call_id, err)

    if current and master_sock not in socks:
        raise ConnectionLost()

class ConnectionLost(Exception):
    pass

idle = 0

def idle_func():
    global idle
    if idle == 1:
        idle = 2
    elif idle == 2:
        idle = -1
        wizard.w_idle()

def run():
    global app, reader
    global current_socket

    from ._types import Application

    args, _ = parser.parse_known_args()

    app = Application.__subclasses__()[0](
        instance_id=args.dice_instance_id,
        workflow_dir=args.dice_workflow_dir,
        progress=args.dice_progress
    )

    reader, writer = socket.socketpair()
    reader.setblocking(0)
    writer.setblocking(0)

    def wake():
        writer.send(b'\x00')

    wizard.setup(wake)

    connect(args.dice_addr, args.dice_port)

    sys.stdout.write = stdout_write
    sys.stderr.write = stderr_write

    timeout = wizard.timeout(idle_func, 0.1, -1)

    try:
        while True:
            process_messages()
    except ConnectionLost:
        pass
    finally:
        wizard.w_idle()
        wizard.w_shutdown()
