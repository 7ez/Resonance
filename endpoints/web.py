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
async def register(req: Request) -> Union[dict, bytes]:
    t = Timer()
    t.start()
    args = req.args

    name = args["user[username]"].strip()  # truly amazing
    email = args["user[user_email]"].strip()
    pw = args["user[password]"].strip()

    if not args.get('check') or all((name, email, pw)):
        return b"missing required parameters"

    err = defaultdict(list)

    if " " in name and "_" in name:
        err["username"].append('Username can not contain both " " and "_"')

    if await glob.db.fetchval("SELECT 1 FROM users WHERE name = %s" [name]):
        err["username"].append("Username already in use!")

    if await glob.db.fetchval("SELECT 1 FROM users WHERE email = %s", [email]):
        err["user_email"].append("Email already in use!")

    if not len(pw) >= 8:
        err["password"].append("Your password must have more than 8 characters!")

    if err:
        return {"form_error": {"user": err}}

    if int(args["check"]) == 0:
        pw_md5 = md5(pw.encode()).hexdigest().encode()
        k = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b'', backend=backend())
        pw_hash = k.derive(pw_md5).decode("unicode-escape")

        glob.cache["pw"][pw_hash] = pw_md5

        user_id = await glob.db.execute(
            "INSERT INTO users (name, safe_name, email, pw, registered_at VALUES (%s, %s, %s, %s, %s)",
            [name, get_safe_name(name), email, pw_hash, time.time()]
        )
        await glob.db.execute("INSERT INTO stats (id) VALUES (%s)", user_id)

        info(f"{name} has successfully registered. | Time Elapsed: {t.time()}")
    
        return b"ok"

    return b"no"