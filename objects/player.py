from dataclasses import dataclass
from typing import Optional, Iterator, Union

from objects import glob
from constants.privileges import Privileges, ClientPrivileges
from helpers.utils import get_safe_name
from constants.modes import osuModes
from constants import packets
from objects.channel import Channel
from helpers.logger import info

@dataclass
class Stats:
    rscore: int
    acc: float
    pc: int
    tscore: int
    rank: int
    country_rank: int
    pp: int
    max_combo: int
    playtime: int

class Player:
    __slots__ = (
        "id",
        "name",
        "safe_name",
        "token",
        "pw",
        "priv",
        "country_iso",
        "country",
        "loc",
        "friends",
        "queue",
        "stats",
        "map_md5",
        "map_id",
        "mode",
        "mode_vn",
        "mods",
        "action",
        "info",
        "login_time",
        "offset",
        "silence_end",
        "restricted",
        "frozen"
    )

    def __init__(self, **kwargs) -> None:
        self.id: Optional[int] = kwargs.get('id')

        self.name: Optional[str] = kwargs.get('name')
        self.safe_name: Optional[str] = get_safe_name(kwargs.get('name'))

        self.token: Optional[str] = kwargs.get('token')
    
        self.pw: Optional[str] = kwargs.get('pw')

        self.priv: Privileges = kwargs.get('priv', Privileges(0))

        self.country_iso: Optional[str] = kwargs.get('country_iso')
        self.country: int = 174 # hardcoded to poland
        self.loc: Optional[list[float]] = kwargs.get("loc", [0.0, 0.0])

        self.friends: set[int] = set()
        
        self.queue = bytearray()

        self.stats: dict[osuModes, Stats] = {}

        self.map_md5: str = ""
        self.map_id: int = 0
        self.mode: int = 0
        self.mode_vn: int = 0
        self.mods: int = 0
        
        self.action: int = 0
        self.info: str = ""

        self.login_time: Optional[int] = kwargs.get('login_time')
        self.offset: Optional[int] = kwargs.get('offset')
        self.silence_end: Optional[int] = kwargs.get('silence_end', 0)

        self.restricted: bool = False
        self.frozen: bool = False

    @classmethod
    async def from_sql(cls, typ: Union[str, int]) -> Optional["Player"]:
        if isinstance(typ, str):
            type = "name"
        elif isinstance(typ, int):
            type = "id"
        else:
            return # :tf:

        user = await glob.db.fetchrow(f"SELECT * FROM users WHERE {type} = %s", [typ])

        if not user:
            return

        self = cls(
            id=user["id"],
            name=user["name"],
            country_iso=user["country"],
            priv=Privileges(user["priv"]),
        )

        return self
        

    @classmethod
    async def login(cls, user: dict) -> "Player":
        self = cls(
            id=user["id"],
            name=user["name"],
            token=user["token"],
            login_time=user["ltime"],
            offset=user["offset"],
            country=user["country"],
            pw=user["md5"].decode(),
            priv=Privileges(user["priv"]),
        )

        glob.players.append(self)

        async for user in glob.db.iter("SELECT user2 FROM friends WHERE user1 = %s", [self.id]):
            self.friends.add(user["user2"])

        if self.priv & Privileges.Restricted:
            self.restricted = True

        if self.priv & Privileges.Frozen:
            self.frozen = True

        return self

    def logout(self) -> None:
        glob.players.remove(self)

        self.token = ""

        if not self.restricted:
            glob.players.enqueue(packets.logout(self.id))

    def enqueue(self, b: bytes) -> None:
        self.queue += b

    def dequeue(self) -> Optional[bytes]:
        if self.queue:
            p = bytes(self.queue)
            self.queue.clear()
            return p

    async def set_stats(self) -> None:
        for mode in osuModes:
            stat = await glob.db.fetchrow(
                "SELECT rscore_{0} rscore, acc_{0} acc, pc_{0} pc, "
                "tscore_{0} tscore, pp_{0} pp, mc_{0} max_combo, "
                "pt_{0} playtime FROM stats WHERE id = %s".format(mode.name),
                [self.id],
            )

            stat["rank"] = 1
            stat["country_rank"] = 1

            self.stats[mode.value] = Stats(**stat)

    @property
    def cur_stats(self) -> Stats:
        return self.stats[self.mode]

    @property
    def client_priv(self) -> ClientPrivileges:
        priv = ClientPrivileges(0)
        priv |= ClientPrivileges.Player
        priv |= ClientPrivileges.Supporter

        if self.restricted:
            return priv

        if self.priv & Privileges.Admin:
            priv |= ClientPrivileges.Moderator
        if self.priv & Privileges.Developer:
            priv |= ClientPrivileges.Developer
        if self.priv & Privileges.Owner:
            priv |= ClientPrivileges.Owner

        return priv

    async def add_friend(self, t: "Player") -> None:
        if t.id in self.friends:
            return

        await glob.db.execute("INSERT INTO friends (user1, user2) VALUES (%s, %s)", [self.id, t.id])
        self.friends.add(t.id)

    async def rm_friend(self, t: "Player") -> None:
        if not t.id in self.friends:
            return

        await glob.db.execute("DELETE FROM friends WHERE user1 = %s AND user2 = %s", [self.id, t.id])
        self.friends.remove(t.id)
    
    def send(self, msg: str, sender: "Player") -> None:
        self.enqueue(
            packets.send_message(
                sender.name,
                msg,
                self.name,
                sender.id
            )
        )

    def join_chan(self, chan: Channel) -> bool:
        if self in chan.players:
            return False

        chan.add_player(self)
        self.enqueue(packets.channel_join(chan.name))
        for u in glob.players:
            u.enqueue(packets.channel_info(chan.name, chan.desc, chan.count))
        info(f"{self.name} joined {chan.name}")

        return True


class PlayerList(list[Player]):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __iter__(self) -> Iterator[Player]:
        return super().__iter__()

    def __contains__(self, user: Player) -> bool:
        if isinstance(user, str):
            return user in [p.name for p in self]
        else:
            return super().__contains__(user)

    # not sure when i'll use these 2 but sure
    @property
    def user_ids(self) -> list[int]:
        return [u.id for u in self]

    @property
    def user_names(self) -> list[str]:
        return [u.name for u in self]

    @property
    def restricted_users(self) -> list[Player]:
        return [u for u in self if u.priv & Privileges.Restricted]

    @property
    def unrestricted_users(self) -> list[Player]:
        return [u for u in self if not u.priv & Privileges.Restricted]

    def enqueue(self, data: bytes, ignored: list[Player] = []) -> None:
        for u in self:
            if u not in ignored:
                u.enqueue(data)

    async def get(self, **kwargs) -> Optional[Player]:
        for _type in ("id", "name", "token"):
            if user := kwargs.pop(_type, None):
                utype = _type
                break
        else:
            return

        for u in self:
            if getattr(u, utype) == user:
                return u
            else:
                if kwargs.get("sql") and utype != "token":
                    return await Player.from_sql(user)

    # kind of useless given we have get(),
    # however packet reader needs non-async func sooo here we are
    def get_online(self, **kwargs) -> Optional[Player]:
        for _type in ("id", "name", "token"):
            if user := kwargs.pop(_type, None):
                utype = _type
                break
        else:
            return

        for u in self:
            if getattr(u, utype) == user:
                return u

    async def find_login(self, name: str, pw: str) -> Optional[Player]:
        user = await self.get(name=name)

        if user and user.pw == pw:
            return user

    def append(self, user: Player) -> None:
        if user not in self:
            super().append(user)

    def remove(self, user: Player) -> None:
        if user in self:
            super().remove(user)
