from multiprocessing.connection import Client
import uuid, time

from xevel import Router, Request
from cryptography.exceptions import InvalidKey
from cryptography.hazmat.backends import default_backend as backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand
from typing import Callable, Type

from objects import glob
from helpers.logger import warning, info, debug
from helpers.timer import Timer
from constants.privileges import Privileges
from constants import packets
from objects.player import Player
from constants.packets import BanchoPacketReader, BasePacket
from constants.packets import ClientPackets

bancho = Router(f"c.{glob.config.domain}")

ROOT_PAGE = f"Resonance v{glob.version}, gone wrong"

def packet(
    packet: ClientPackets,
    allow_res: bool = False,
) -> Callable[[Type[BasePacket]], Type[BasePacket]]:

    def wrapper(cls: Type[BasePacket]) -> Type[BasePacket]:
        glob.packets[packet] = cls

        if allow_res:
            glob.packets[packet] = cls

        return cls

    return wrapper

@packet(ClientPackets.LOGOUT, True)
class Logout(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        reader.read_i32()

    async def handle(self, p: Player) -> None:
        if (time.time() - p.login_time) < 0.3: # 300ms
            return

        p.logout()
        info(f"{p.name} has logged out.")
        
@packet(ClientPackets.FRIEND_ADD, True)
class AddFriend(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.uid = reader.read_i32()

    async def handle(self, p: Player) -> None:
        if not (t := await glob.players.get(id=self.uid)):
            info(f"{p.name} tried adding {t.name} when they're offline!")
            return

        await p.add_friend(t)

@packet(ClientPackets.FRIEND_REMOVE, True)
class RemoveFriend(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.uid = reader.read_i32()

    async def handle(self, p: Player) -> None:
        if not (t := await glob.players.get(id=self.uid)):
            info(f"{p.name} tried removing {t.name} when they're offline!")
            return

        await p.rm_friend(t)

@packet(ClientPackets.SEND_PRIVATE_MESSAGE)
class SendPM(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.msg = reader.read_message()
    
    async def handle(self, p: Player) -> None:
        if p.silence_end > time.time():
            info(f"{p.name} tried sending a message while silenced.")
            return

        msg = self.msg.text.strip()

        if not msg:
            return

        t_user = self.msg.recipient

        if not (t := await glob.players.get(name=t_user)):
            info(f"{p.name} tried to send a message to a offline/non-existent user.")
            return

        if t.silence_end > time.time():
            p.enqueue(packets.target_silenced(t.name))

        if len(msg) > 2000: # idk why but yeah
            msg = f"{msg[:2000]}..."

        t.send(msg, p)

@packet(ClientPackets.CHANNEL_JOIN, True)
class ChannelJoin(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.name = reader.read_string()

    async def handle(self, p: Player) -> None:
        chan = glob.channels[self.name]

        if not chan or not p.join_chan(chan):
            warning(f"{p.name} failed to join channel {self.name}")
            return

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
            except InvalidKey:
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
        await p.set_stats()

        resp = bytearray(
            packets.user_id(p.id),
        )

        user_info = packets.user_presence(p) + packets.user_stats(p)
        
        for chan in glob.channels.values():
            if chan.auto:
                p.join_chan(chan)
                

        resp += packets.protocol_version(19)
        resp += packets.bancho_privileges(p.client_priv)   
        resp += user_info
        resp += packets.channel_info_end()
        resp += packets.main_menu_icon(**glob.config.menu_icon)
        resp += packets.friends_list(*p.friends)
        resp += packets.silence_end(0)
        resp += packets.notification(f"Welcome to Resonance v{glob.version}, {p.name}!\nTime Elapsed: {t.time()}")

        for u in glob.players:
            if not u.restricted:
                resp += packets.user_presence(u) + packets.user_stats(u)
            if not p.restricted:
                u.enqueue(user_info)


        info(f"{p.name} logged in successfully. | Time Elapsed: {t.time()}")

        req.resp_headers["cho-token"] = token
        return bytes(resp)

    user_token = headers["osu-token"]
    if not (p := await glob.players.get(token=user_token)):
        return packets.restart_server(0)

    body = req.body

    if not p.restricted:
        ap = glob.packets
    else:
        ap = glob.packets_res

    with memoryview(body) as body_view:
        for packet in BanchoPacketReader(body_view, ap):
            await packet.handle(p)
            debug(f"Packet {packet.__class__.__name__} handled for {p.name}")

    return p.dequeue() or b""