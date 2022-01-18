from optparse import Option
from typing import Optional

from objects import glob
from objects.privileges import Privileges
from helpers.utils import get_safe_name

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
        "login_time",
        "offset",
        "silence_end",
        "action",
        "info",
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
        self.country: Optional[int] = kwargs.get('country')
        self.loc: Optional[list[float]] = kwargs.get("loc", [0.0, 0.0])

        self.friends: set[int] = ()
        
        self.queue = bytearray()

        self.login_time: Optional[int] = kwargs.get('login_time')
        self.login_time: Optional[int] = kwargs.get('offset')
        self.silence_end: Optional[int] = kwargs.get('silence_end', 0)

        self.action: int = 0
        self.info: str = ""

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

        self.friends + self.id

        if self.priv & Privileges.Restricted:
            self.restricted = True

        if self.priv & Privileges.Frozen:
            self.frozen = True

        return self
