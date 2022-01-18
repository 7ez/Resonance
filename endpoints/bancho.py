import uuid

from xevel import Router, Request

from objects import glob, packets
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
        pw = user_data[1] # currently using md5 auth (LOL) fr tho im just too lazy to think of which pw hash thingy to use

        # user = await glob.db.fetchrow("SELECT * FROM users WHERE name = %s", [username])
        user = { # debug purposes
            "name": "Aochi",
            "pw": pw,
            "priv": 3
        }
        
        if not user:
            req.resp_headers["cho-token"] = "no"
            return packets.user_id(1)

        if user["pw"] != pw:
            req.resp_headers["cho-token"] = "no"
            return packets.user_id(-1)
        
        if user["priv"] & Privileges.Banned:
            req.resp_headers["cho-token"] = "no"
            return packets.user_id(-3)

        token = uuid.uuid4()

        resp = bytearray(
            packets.user_id(3),
        )

        resp += packets.protocol_version(19)
        resp += packets.bancho_privileges(ClientPrivileges.Player | ClientPrivileges.Supporter)
        resp += packets.bot_presence(3, "Aochi") + packets.bot_stats(3)
        resp += packets.channel_info_end()
        resp += packets.main_menu_icon(
            icon_url = "https://cdn.discordapp.com/avatars/272111921610752003/7c6ed0fca6122c3b5a0028444d4f1ee3.webp?size=80",
            onclick_url = "https://fuquila.net"
        )
        resp += packets.friends_list(3)
        resp += packets.silence_end(0)
        resp += packets.notification(f"Welcome to Resonance v{glob.version}, {user['name']}!\nTook: {t.time()}")

        req.resp_headers["cho-token"] = token
        return token, bytes(resp)
        
