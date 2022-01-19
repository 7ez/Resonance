from typing import Optional, TYPE_CHECKING

from objects import glob

if TYPE_CHECKING:
    from objects.player import Player


class Channel:
    __slots__ = (
        "name",
        "desc",
        "perm",
        "auto",
        "players"
    )

    def __init__(self, **kwargs):
        self.name: Optional[str] = kwargs.get("name")

        self.desc: Optional[str] = kwargs.get("desc")

        self.perm: bool = kwargs.get('perm', False)
        self.auto: bool = kwargs.get('auto', False)

        self.players: list = []


    def add_player(self, u: "Player") -> None:
        self.players.append(u)
    
    def rm_player(self, u: "Player") -> None:
        self.players.remove(u)

        if not len(self.players) and not self.perm:
            glob.channels.remove(self)

    @property
    def count(self) -> int:
        return len(self.players)
        
    @staticmethod
    def enqueue(b: bytes, ignore: int = 0, ignore_list: list["Player"] = []) -> None:
        ignore_list.append(glob.players.get_online(id=ignore))

        glob.players.enqueue(b, ignore_list)

    