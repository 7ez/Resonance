import uuid, time
from objects.player import Player

from xevel import Router, Request
from cryptography.hazmat.backends import default_backend as backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand

from objects import glob, packets
from helpers.logger import warning, info
from helpers.timer import Timer
from objects.privileges import Privileges, ClientPrivileges

bancho = Router(f"c.{glob.config.domain}")

ROOT_PAGE = f"Resonance v{glob.version}, gone wrong"

@bancho.route("/", ["GET", "POST"])
async def login(req: Request) -> bytes:
    t = Timer()
    headers = req.headers
    t.start()
    
    if ("User-Agent" not in headers or headers["User-Agent"] != "osu!" or req.type == "GET"):
        return ROOT_PAGE.encode()

    if "osu-token" not in headers:
        if len(user_data := (req.body).decode().split("\n")[:-1]) != 3:
            req.resp_headers["cho-token"] = "no"
            return packets.user_id(-2)

        if len(client_hash := user_data[2].split("|")) != 5:
            req.resp_headers["cho-token"] = "no"
            return packets.user_id(-2)
        
        username = user_data[0]
        pw = user_data[1].encode()
        pw_cache = glob.cache["pw"]

        user = await glob.db.fetchrow("SELECT * FROM users WHERE name = %s", [username])
        
        if not user:
            warning(f"{username}'s login failed; User doesn't exist.")
            req.resp_headers["cho-token"] = "no"
            return packets.user_id(-1)

        user_pw = user["pw"].encode("ISO-8859-1").decode('unicode-escape').encode("ISO-8859-1")

        if pw in pw_cache:
            if pw != pw_cache[user_pw]:
                warning(f"{username}'s login failed; Invalid password.")
                req.resp_headers["cho-token"] = "no"
                return packets.user_id(-1)
        else:
            k = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b'', backend=backend())
            try:
                k.verify(pw, user_pw)
            except Exception:
                warning(f"{username}'s login failed; Invalid password.")
                req.resp_headers["cho-token"] = "no"
                return packets.user_id(-1)

        glob.cache[user_pw] = pw

        if user["priv"] & Privileges.Banned:
            req.resp_headers["cho-token"] = "no"
            return packets.user_id(-3)

        token = uuid.uuid4()
        user["offset"] = int(client_hash[1])
        user["token"] = str(token)
        user["ltime"] = time.time()
        user["md5"] = pw

        p = await Player.login(user)

        resp = bytearray(
            packets.user_id(p.id),
        )

        resp += packets.protocol_version(19)
        resp += packets.bancho_privileges(ClientPrivileges.Player | ClientPrivileges.Supporter)
        resp += packets.bot_presence(p) + packets.bot_stats(p)
        resp += packets.channel_info_end()
        resp += packets.main_menu_icon(
            icon_url = "https://cdn.discordapp.com/avatars/272111921610752003/7c6ed0fca6122c3b5a0028444d4f1ee3.webp?size=80",
            onclick_url = "https://fuquila.net"
        )
        resp += packets.friends_list(p.friends)
        resp += packets.silence_end(0)
        resp += packets.notification(f"Welcome to Resonance v{glob.version}, {p.name}!\nTook: {t.time()}")

        req.resp_headers["cho-token"] = token
        return bytes(resp)
        
