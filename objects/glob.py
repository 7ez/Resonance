import config # indirect use

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fatFuckSQL import fatFawkSQL
    from cmyui import Version
    from .player import PlayerList


db: 'fatFawkSQL'
version: 'Version'
players: 'PlayerList'

packets = {}
packets_res = {}

cache = {
    'pw': {}
}