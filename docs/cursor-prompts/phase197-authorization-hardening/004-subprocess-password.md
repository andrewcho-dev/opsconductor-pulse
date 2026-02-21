# Task 4: Fix MQTT Password Subprocess Exposure

## Context

`services/provision_api/app.py:90-96` calls `mosquitto_passwd` with the password as a command-line argument:
```python
subprocess.run([passwd_tool, "-b", MQTT_PASSWD_FILE, username, password], ...)
```

On Linux, process arguments are visible in `/proc/<pid>/cmdline` to any user on the host, and in `ps aux` output. The password is exposed in plaintext.

## Actions

1. Read `services/provision_api/app.py` in full, focusing on the MQTT password management section.

2. Determine which MQTT password file format is being used. `mosquitto_passwd -b` creates a bcrypt-hashed password file. The hash can be computed directly in Python using the `passlib` library without spawning a subprocess.

3. Check whether `passlib` is in the service's `requirements.txt`. If not, add it.

4. Replace the subprocess call with a direct Python implementation:

```python
from passlib.hash import bcrypt as passlib_bcrypt
import os

def update_mqtt_password(passwd_file: str, username: str, password: str) -> None:
    """
    Update MQTT password file without exposing password in subprocess args.
    Uses same bcrypt format as mosquitto_passwd.
    """
    # Read existing entries
    entries: dict[str, str] = {}
    if os.path.exists(passwd_file):
        with open(passwd_file, "r") as f:
            for line in f:
                line = line.strip()
                if ":" in line:
                    u, h = line.split(":", 1)
                    entries[u] = h

    # Hash the new password (mosquitto uses bcrypt with cost factor 12)
    hashed = passlib_bcrypt.using(rounds=12).hash(password)
    entries[username] = f"$7${hashed}"  # mosquitto v2 prefix

    # Write back atomically
    tmp_file = passwd_file + ".tmp"
    with open(tmp_file, "w") as f:
        for u, h in entries.items():
            f.write(f"{u}:{h}\n")
    os.replace(tmp_file, passwd_file)
```

5. Replace the `subprocess.run(...)` call with `update_mqtt_password(MQTT_PASSWD_FILE, username, password)`.

6. If the bcrypt format or prefix differs from what EMQX actually expects, adjust accordingly. Read the EMQX documentation or examine the existing password file format before assuming the format above is correct.

7. Remove the `passwd_tool` lookup and any related subprocess imports if they're no longer needed.

## Verification

```bash
grep -n 'subprocess' services/provision_api/app.py
# Must return zero results for password-related subprocess calls

grep -n 'passlib\|bcrypt' services/provision_api/app.py
# Must show library-based password hashing
```
