from dataclasses import dataclass
from typing import Optional

from objects import glob
from constants.privileges import Privileges, ClientPrivileges
from helpers.utils import get_safe_name
from constants.modes import osuModes

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
        self.country: Optional[int] = kwargs.get('country', 616)
        self.loc: Optional[list[float]] = kwargs.get("loc", [0.0, 0.0])

        self.friends: set[int] = set()
        
        self.queue = bytearray(),

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

        self.friends.add(self.id)

        if self.priv & Privileges.Restricted:
            self.restricted = True

        if self.priv & Privileges.Frozen:
            self.frozen = True

        return self

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