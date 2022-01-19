#!/usr/bin/python3.9

from xevel import Xevel, Request
from fatFuckSQL import fatFawkSQL
from cmyui import Version

from objects import glob
from helpers.logger import info, error, debug
from objects.player import PlayerList

app = Xevel(glob.config.socket)
glob.version = Version(0, 1, 4)

@app.before_serving()
async def connect() -> None:
    debug(f"Resonance v{glob.version} starting")
    glob.players = PlayerList()
    try:
        glob.db = await fatFawkSQL.connect(**glob.config.mysql)
        debug("Connected to MySQL!")
    except Exception as e:
        error(f"Failed to connect to MySQL!\n\n{e}")
        raise SystemExit(1)
    info(f"Resonance v{glob.version} started")

if glob.config.debug:
    @app.after_request()
    async def logRequest(resp: Request) -> Request:
        if resp.code >= 400:
            log_func = error
        else:
            log_func = info

        log_func(
            f"[{resp.type}] {resp.code} {resp.url} | Time Elapsed: {resp.elapsed}",
        )
        return resp

@app.after_serving()
async def disconnect() -> None:
    debug(f"Resonance v{glob.version} stopping")

    await glob.db.close()

    info(f"Resonance v{glob.version} stopped")

if __name__ == '__main__':
    from endpoints.bancho import bancho
    from endpoints.web import web

    app.add_router(bancho)
    app.add_router(web)

    app.start()
else:
    info("Run Resonance directly (`./main.py`)")
    raise SystemExit(1)