import time
from typing import Union
from xevel import Router, Request
from cryptography.hazmat.backends import default_backend as backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand
from hashlib import md5
from collections import defaultdict

from objects import glob
from helpers.timer import Timer
from helpers.utils import get_safe_name
from helpers.logger import info

web = Router(f'osu.{glob.config.domain}')

@web.route("/users", ["POST"])
async def ingameRegistration(request: Request) -> Union[dict, bytes]:
    t = Timer()
    t.start()
    pargs = request.args

    name = pargs["user[username]"].strip()
    email = pargs["user[user_email]"].strip()
    pw = pargs["user[password]"].strip()

    if not pargs.get("check") or not all((name, email, pw)):
        return b"missing required paramaters"

    errors = defaultdict(list)
    if " " in name and "_" in name:
        errors["username"].append('Username cannot contain both "_" and " "')

    if await glob.db.fetchval("SELECT 1 FROM users WHERE name = %s", [name]):
        errors["username"].append("Username already in use!")

    if await glob.db.fetchval("SELECT 1 FROM users WHERE email = %s", [email]):
        errors["user_email"].append("Email already in use!")

    if not len(pw) >= 8:
        errors["password"].append("Password must have more than 8 characters")

    if errors:
        return {"form_error": {"user": errors}}

    if int(pargs["check"]) == 0:
        pw_md5 = md5(pw.encode()).hexdigest().encode()
        k = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b"", backend=backend())
        pw_hash = k.derive(md5).decode("unicode-escape")

        glob.cache["pw"][pw_hash] = pw_md5

        uid = await glob.db.execute(
            "INSERT INTO users (name, email, pw, safe_name, registered_at) VALUES (%s, %s, %s, %s, %s)",
            [name, email, pw_hash, get_safe_name(name), time.time()],
        )
        await glob.db.execute("INSERT INTO stats (id) VALUES (%s)", [uid])
        info(f"{name} successfully registered. | Time Elapsed: ",)
    
    return b"ok"