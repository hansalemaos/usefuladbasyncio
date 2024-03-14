

# asyncio version of usefuladb

## Documentation: https://github.com/hansalemaos/usefuladb

### pip install usefuladbasyncio


```python
# Tested against Android 11 / Bluestacks / Python 3.11 / Windows 10

from usefuladbasyncio import AdbAsyncIO
import time

adb = AdbAsyncIO(
    adb_path=r"C:\ProgramData\chocolatey\lib\adb\tools\platform-tools\adb.exe",
    device_serial="127.0.0.1:5555",
    use_busybox=False,
    connect_to_device=True,
    invisible=True,
    print_stdout=True,
    print_stderr=True,
    limit_stdout=None,
    limit_stderr=None,
    limit_stdin=None,
    convert_to_83=True,
    wait_to_complete=15,
    flush_stdout_before=True,
    flush_stdin_before=True,
    flush_stderr_before=True,
    su=False,
    exitcommand="xxxCOMMANDxxxDONExxx",
    commandtimeout=10,
    escape_filepath=True,
    capture_stdout_stderr_first=True,
    global_cmd=False,
    global_cmd_timeout=15,
    use_eval=False,
    eval_timeout=30,
    stdoutsleep=0.5,
    stderrsleep=0.5,
    asynciosleep=0,
    daemon=True,
    reconnect_interval=2,
)
while True:
    # can reconnect if the connection gets lost
    a, b = adb.execute_sh_command(
        "ls /sdcard/ -R",
        stdoutsleep=1,
        stderrsleep=1,
        asynciosleep=0,
        disable_print_stdout=True,
        disable_print_stderr=True,
    )
    c, d = adb.sh_ls_folder("/sdcard/") # i haven't tested all methods of usefuladb yet
    print(c, d)
    print([a, b])
    time.sleep(1)

```