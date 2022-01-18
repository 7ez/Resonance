from xevel import Xevel
from fatFuckSQL import fatFawkSQL
from cmyui import Version

from objects import glob
from helpers.logger import info, error

app = Xevel(glob.config.socket)
glob.version = Version(0, 0, 2)

@app.before_serving()
async def connect() -> None:
    info(f"Resonance v{glob.version} starting")    
    try:
        # glob.db = await fatFawkSQL.connect(**glob.config.mysql) # testing and i dont use a db
        ("Connected to MySQL!")
    except Exception as e:
        error(f"Failed to connect to MySQL!\n\n{e}")
        raise SystemExit(1)
    info(f"Resonance v{glob.version} started")


if __name__ == '__main__':
    from endpoints.bancho import bancho

    app.add_router(bancho)
    app.run()
else:
    info("Run Resonance directly (`./main.py`)")
    raise SystemExit(1)