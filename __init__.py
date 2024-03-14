import ast
import threading
import asyncio, subprocess, sys
import kthread
import time
from usefuladb import AdbControl, invisibledict, get_short_path_name
import pprint


async def send_command(p, cmd):
    if isinstance(cmd, str):
        p.stdin.write(cmd.encode() + b"\n")
    else:
        p.stdin.write(cmd + b"\n")
    await p.stdin.drain()


async def main(
    cmd,
    **kwargs,
):
    allcommands = kwargs.get("allcommands", [])
    stdoutdata = kwargs.get("stdoutdata", [])
    stderrdata = kwargs.get("stderrdata", [])
    stdoutsleep = kwargs.get("stdoutsleep", [0.5])
    stderrsleep = kwargs.get("stderrsleep", [0.5])
    asynciosleep = kwargs.get("asynciosleep", [0])
    stoptrigger = kwargs.get("stoptrigger", [False])
    print_stdout = kwargs.get("print_stdout", [True])
    print_stderr = kwargs.get("print_stderr", [True])
    exitcommand = kwargs.get("exitcommand", b"xxxCOMMANDxxxDONExxx")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        **invisibledict,
    )

    while not stoptrigger[0]:
        if allcommands:
            await send_command(proc, allcommands.pop(0))
        else:
            await asyncio.sleep(asynciosleep[0])
        try:
            stdoutdata.append(
                await asyncio.wait_for(
                    proc.stdout.readline(),
                    timeout=stdoutsleep[0],
                )
            )
            if print_stdout[0]:
                print(stdoutdata[-1])
        except asyncio.TimeoutError:
            try:
                stderrdata.append(
                    await asyncio.wait_for(
                        proc.stderr.readline(),
                        timeout=stderrsleep[0],
                    )
                )
                if print_stderr[0]:
                    print(stderrdata[-1])
            except asyncio.TimeoutError:
                pass


def run_main(*args, **kwargs):
    try:
        asyncio.run(main(*args, **kwargs))
    except Exception as e:
        kwargs.get("stoptrigger").append(True)
        kwargs.get("stoptrigger").pop(0)
        time.sleep(kwargs.get("reconnect_interval"))
        while True:
            prre = subprocess.run(
                [kwargs.get("adb_path"), "connect", kwargs.get("device_serial")],
                capture_output=True,
                **invisibledict,
            )
            if prre.stdout.startswith(b"already") or prre.stdout.startswith(
                b"connected"
            ):
                time.sleep(5)
                kwargs.get("stoptrigger").append(False)
                kwargs.get("stoptrigger").pop(0)
                break
            time.sleep(kwargs.get("reconnect_interval"))


class AdbAsyncIO(AdbControl):
    def __init__(
        self,
        adb_path,
        device_serial,
        use_busybox=False,  # not implemented
        connect_to_device=True,
        invisible=True,  # always
        print_stdout=False,
        print_stderr=False,
        limit_stdout=None,
        limit_stderr=None,
        limit_stdin=None,
        convert_to_83=True,
        wait_to_complete=30,
        flush_stdout_before=True,
        flush_stdin_before=True,
        flush_stderr_before=True,
        su=False,
        exitcommand="xxxCOMMANDxxxDONExxx",
        commandtimeout=5,
        escape_filepath=True,
        capture_stdout_stderr_first=True,
        global_cmd=True,
        global_cmd_timeout=15,
        use_eval=False,
        eval_timeout=30,
        stdoutsleep=0.5,
        stderrsleep=0.5,
        asynciosleep=0,
        daemon=True,
        reconnect_interval=10,
    ):
        super().__init__(
            adb_path=adb_path,
            device_serial=device_serial,
            use_busybox=use_busybox,
            connect_to_device=False,
            invisible=invisible,
            print_stdout=print_stdout,
            print_stderr=print_stderr,
            limit_stdout=limit_stdout,
            limit_stderr=limit_stderr,
            limit_stdin=limit_stdin,
            convert_to_83=convert_to_83,
            wait_to_complete=wait_to_complete,
            flush_stdout_before=flush_stdout_before,
            flush_stdin_before=flush_stdin_before,
            flush_stderr_before=flush_stderr_before,
            exitcommand=exitcommand,
            capture_stdout_stderr_first=capture_stdout_stderr_first,
            global_cmd=global_cmd,
            global_cmd_timeout=global_cmd_timeout,
            use_eval=use_eval,
            eval_timeout=eval_timeout,
        )
        self.reconnect_interval = reconnect_interval
        self.adbpath = adb_path
        self.device_serial = device_serial
        if convert_to_83:
            self.adb_path = get_short_path_name(adb_path)
        else:
            self.adb_path = adb_path
        if connect_to_device:
            subprocess.run([self.adb_path, "connect", device_serial], **invisibledict)
        self.device_serial = device_serial
        self.convert_to_83 = convert_to_83
        self.exitcommand = exitcommand
        self.capture_stdout_stderr_first = capture_stdout_stderr_first
        self.global_cmd = global_cmd
        self.su = su
        self.use_busybox = use_busybox
        self.adbpath = adb_path
        self.device_serial = device_serial
        if convert_to_83:
            self.adb_path = get_short_path_name(adb_path)
        else:
            self.adb_path = adb_path
        self.wait_to_complete = wait_to_complete
        self.flush_stdout_before = flush_stdout_before
        self.flush_stdin_before = flush_stdin_before
        self.flush_stderr_before = flush_stderr_before
        self.invisible = invisible
        self.print_stdout = [print_stdout]
        self.print_stderr = [print_stderr]
        self.limit_stdout = limit_stdout
        self.limit_stderr = limit_stderr
        self.limit_stdin = limit_stdin
        self.convert_to_83 = convert_to_83
        self.exitcommand = exitcommand
        self.commandtimeout = commandtimeout
        self.escape_filepath = escape_filepath
        self.global_cmd = global_cmd
        self.global_cmd_timeout = global_cmd_timeout
        self.use_eval = use_eval
        self.eval_timeout = eval_timeout
        self.stdoutsleep = [stdoutsleep]
        self.stderrsleep = [stderrsleep]
        self.asynciosleep = [asynciosleep]
        self.lockobject = threading.Lock()

        self.allcommands = []
        self.stdout = []
        self.stderr = []

        self.stoptrigger = [False]
        self.daemon = daemon
        self.threadstart = kthread.KThread(
            target=run_main,
            kwargs={
                "allcommands": self.allcommands,
                "stderrdata": self.stderr,
                "stdoutdata": self.stdout,
                "cmd": (self.adb_path, "-s", self.device_serial, "shell"),
                "stoptrigger": self.stoptrigger,
                "stderrsleep": self.stderrsleep,
                "stdoutsleep": self.stdoutsleep,
                "asynciosleep": self.asynciosleep,
                "exitcommand": self.exitcommand,
                "print_stdout": self.print_stdout,
                "print_stderr": self.print_stderr,
                "adb_path": self.adb_path,
                "device_serial": self.device_serial,
                "reconnect_interval": self.reconnect_interval,
            },
            name=device_serial,
            daemon=self.daemon,
        )
        self.threadstart.start()

    def execute_sh_command(self, cmd, **kwargs):
        doreconnect = False
        while self.stoptrigger[0]:
            print("Not connected... trying to reconnect", end="\r")
            doreconnect = True
            time.sleep(1)
        if doreconnect:
            print()
            self.flush_stderr()
            self.flush_stderr()
            self.flush_stdout()
            time.sleep(3)
            self.threadstart = kthread.KThread(
                target=run_main,
                kwargs={
                    "allcommands": self.allcommands,
                    "stderrdata": self.stderr,
                    "stdoutdata": self.stdout,
                    "cmd": (self.adb_path, "-s", self.device_serial, "shell"),
                    "stoptrigger": self.stoptrigger,
                    "stderrsleep": self.stderrsleep,
                    "stdoutsleep": self.stdoutsleep,
                    "asynciosleep": self.asynciosleep,
                    "exitcommand": self.exitcommand,
                    "print_stdout": self.print_stdout,
                    "print_stderr": self.print_stderr,
                    "adb_path": self.adb_path,
                    "device_serial": self.device_serial,
                    "reconnect_interval": self.reconnect_interval,
                },
                name=self.device_serial,
                daemon=self.daemon,
            )
            self.threadstart.start()
            time.sleep(1)
        return self._execute_sh_commandasync(cmd, **kwargs)

    def _execute_sh_commandasync(self, cmd, **kwargs):
        self._correct_newlines = True
        if isinstance(cmd, str):
            try:
                stackframe = sys._getframe(1)
                for key, item in stackframe.f_locals.items():
                    if isinstance(item, bytes):
                        asstr = str(item)
                        if asstr in cmd:
                            cmd = cmd.replace(asstr, asstr[2:-1])
            except Exception as fe:
                sys.stderr.write(f"{fe}\n")
                sys.stderr.flush()

        # evalcmd = kwargs.get("use_eval", self.use_eval)
        oldvaluestdout = self.print_stdout[0]
        oldvaluestderr = self.print_stderr[0]

        disable_print_stdout = kwargs.get(
            "disable_print_stdout", not self.print_stdout[0]
        )
        disable_print_stderr = kwargs.get(
            "disable_print_stderr", not self.print_stderr[0]
        )
        wait_to_complete = kwargs.get("wait_to_complete", self.wait_to_complete)
        flush_stdout_before = kwargs.get(
            "flush_stdout_before", self.flush_stdout_before
        )
        flush_stdin_before = kwargs.get("flush_stdin_before", self.flush_stdin_before)
        flush_stderr_before = kwargs.get(
            "flush_stderr_before", self.flush_stderr_before
        )
        exitcommand = kwargs.get("exitcommand", self.exitcommand)
        su = kwargs.get("su", self.su)
        commandtimeout = kwargs.get("commandtimeout", self.commandtimeout)
        if "escape_filepath" in kwargs:
            del kwargs["escape_filepath"]
        capture_stdout_stderr_first = kwargs.get(
            "capture_stdout_stderr_first", self.capture_stdout_stderr_first
        )
        if "disable_print_stdout" in kwargs:
            if disable_print_stdout:
                self.print_stdout.append(False)

                self.print_stdout.pop(0)
            else:
                self.print_stdout.append(True)

                self.print_stdout.pop(0)
        if "disable_print_stderr" in kwargs:
            if disable_print_stderr:
                self.print_stderr.append(False)

                self.print_stderr.pop(0)
            else:
                self.print_stderr.append(True)

                self.print_stderr.pop(0)
        if flush_stdin_before:
            self.flush_stderr()
        if flush_stderr_before:
            self.flush_stderr()
        if flush_stdout_before:
            self.flush_stdout()
        if not wait_to_complete:
            exitcommand = ""
        try:
            if (cmd.startswith('b"') and cmd.endswith('"')) or (
                cmd.startswith("b'") and cmd.endswith("'")
            ):
                cmd = ast.literal_eval(str(cmd.encode("utf-8")))
        except Exception:
            pass
        encodedexit = f"{exitcommand}".encode("utf-8") + b"\r\n"
        countexitout = self.stdout.count(encodedexit)
        countexiterr = self.stderr.count(encodedexit)
        if not isinstance(cmd, bytes):
            cmd = cmd.encode()
        command2execute = cmd + (
            f""" && echo "{exitcommand}" || echo "{exitcommand}" >&2"""
        ).encode("utf-8")
        if su:
            command2execute = b"#!/bin/bash\nsu\n" + cmd
        self.allcommands.append(command2execute)
        stdoutsleep_old = self.stdoutsleep[0]
        stderrsleep_old = self.stderrsleep[0]
        asynciosleep_old = self.asynciosleep[0]
        if "stdoutsleep" in kwargs:
            self.stdoutsleep.append(kwargs["stdoutsleep"])
            self.stdoutsleep.pop(0)
        if "stderrsleep" in kwargs:
            self.stderrsleep.append(kwargs["stderrsleep"])
            self.stderrsleep.pop(0)
        if "asynciosleep" in kwargs:
            self.asynciosleep.append(kwargs["asynciosleep"])
            self.asynciosleep.pop(0)

        commandfinaltimeout = time.time() + commandtimeout
        while (
            countexitout >= self.stdout.count(encodedexit)
            and countexiterr >= self.stderr.count(encodedexit)
            and commandfinaltimeout > time.time()
        ):
            time.sleep(0.1)

        if "stdoutsleep" in kwargs:
            self.stdoutsleep.append(stdoutsleep_old)
            self.stdoutsleep.pop(0)
        if "stderrsleep" in kwargs:
            self.stderrsleep.append(stderrsleep_old)
            self.stderrsleep.pop(0)
        if "asynciosleep" in kwargs:
            self.asynciosleep.append(asynciosleep_old)
            self.asynciosleep.pop(0)
        if "disable_print_stdout" in kwargs:
            self.print_stdout.append(oldvaluestdout)

            self.print_stdout.pop(0)
        if "disable_print_stderr" in kwargs:
            self.print_stderr.append(oldvaluestderr)

            self.print_stderr.pop(0)
        a = self.stdout.copy()
        b = self.stderr.copy()
        try:
            a = a[: (len(a) - list(reversed(a)).index(encodedexit)) - 1]
            a = [x.replace(b"\r\n", b"\n") for x in a]
        except Exception:
            pass
        try:
            b = b[: (len(b) - list(reversed(b)).index(encodedexit)) - 1]
            b = [x.replace(b"\r\n", b"\n") for x in b]
        except Exception:
            pass

        return [a, b]


