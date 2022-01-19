#!/usr/bin/python3.9

from xevel import Xevel
from fatFuckSQL import fatFawkSQL
from cmyui import Version

from objects import glob
from helpers.logger import info, error

app = Xevel(glob.config.socket)
glob.version = Version(0, 1, 1)

@app.before_serving()
async def connect() -> None:
    info(f"Resonance v{glob.version} starting")    
    try:
        glob.db = await fatFawkSQL.connect(**glob.config.mysql)
        info("Connected to MySQL!")
    except Exception as e:
        error(f"Failed to connect to MySQL!\n\n{e}")
        raise SystemExit(1)
    info(f"Resonance v{glob.version} started")


@app.after_serving()
async def disconnect() -> None:
    info(f"Resonance v{glob.version} starting")

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