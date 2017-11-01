# Standard Python modules
# =======================
import os
import subprocess
import sys
import io
from threading import Thread
from queue import Queue, Empty
import shlex
import signal
import locale
import codecs
import psutil

# DICE modules
# =======================
from dice_tools import process_messages


def run_process(*args, command=None, stop=None, stdout=None,
        stderr=None, cwd=None, format_kwargs=None,
        yield_func=process_messages, **kwargs):
    
    if isinstance(command, dict):
        if 'cwd' in command:
            command_cwd = command['cwd']
            if format_kwargs:
                command_cwd = command_cwd.format(**format_kwargs)
            command_cwd = os.path.expandvars(command_cwd)
            if not os.path.isabs(command_cwd) and cwd:
                cwd = os.path.join(cwd, command_cwd)
            else:
                cwd = command_cwd
        if 'args' in command:
            args = tuple(command['args']) + args

    elif isinstance(command, str):
        args = tuple(shlex.split(command)) + args

    if format_kwargs:
        args = [v.format(**format_kwargs) for v in args]

    print('running: %s'%' '.join([shlex.quote(v) for v in args]))

    proc = subprocess.Popen(args, cwd=cwd, stdout = subprocess.PIPE,
        stderr = subprocess.PIPE, **kwargs)

    def wait():
        proc.wait()
        q.put(lambda: None)

    def kill(proc_pid):
        process = psutil.Process(proc_pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()

    def read(stream, out):
        """
        Function for stoud/stderr
        """
        if isinstance(stream, io.TextIOWrapper):
            # for unicode
            if callable(out):
                result = ''
                for char in iter(lambda: stream.read(1), ''):
                    if char in ('\n', '\r'):
                        if result:
                            q.put(lambda o=result: out(o))
                            result = ''
                    else:
                        result += char
                if result:
                    q.put(lambda o=result[:-1]: out(o))
            elif isinstance(out, io.StringIO):
                for data in iter(stream.read, b''):
                    out.write(data)
            elif isinstance(out, io.BytesIO):
                for data in iter(stream.read, b''):
                    out.write(data.encode('utf8'))
        else:
            # For binary  data
            if callable(out):
                encoding = locale.getpreferredencoding(False)
                result = ''
                it = iter(lambda: stream.read(1), b'')
                for char in codecs.iterdecode(it, encoding, errors='ignore'):
                    if char in ('\n', '\r'):
                        q.put(lambda o=result: out(o))
                        result = ''
                    else:
                        result += char
                if result:
                    q.put(lambda o=result[:-1]: out(o))
            elif isinstance(out, io.StringIO):
                encoding = locale.getpreferredencoding(False)
                it = iter(stream.read, b'')
                for data in codecs.iterdecode(it, encoding, errors='ignore'):
                    out.write(data)
            elif isinstance(out, io.BytesIO):
                for data in iter(stream.read, b''):
                    out.write(data)

    q = Queue()        
    running = True
    exc = None

    threads = [ Thread(target = wait, daemon=True) ]

    if stdout is not None:
        th = Thread(target = read, daemon=True, args=(proc.stdout, stdout))      
        threads.append(th)

    if stderr is not None:
        th = Thread(target = read, daemon=True, args=(proc.stderr, stderr))      
        threads.append(th)

    for v in threads:
        v.start()

    while True:
        try:
            while True:
                if yield_func is not None:
                    yield_func()
                if running and stop is not None and stop():
                    try:
                        print('Killing process ...')
                        print('PID:', proc.pid)
                        kill(proc.pid)
                    except:
                        pass
                    print('process terminated!')
                    running = False
                alive = any((v.is_alive() for v in threads))
                try:
                    q.get(alive, timeout=0.1)()
                except Empty:
                    if not alive:
                        break
            break
        except KeyboardInterrupt as e:
            if running:
                print('process interrupted!')
                try:
                    kill(proc.pid)
                except:
                    pass
                running = False
                exc = e

    if exc:
        raise exc
    else:
        return proc.returncode