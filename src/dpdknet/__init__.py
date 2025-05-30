from threading import Lock as _Lock

from sqlalchemy import Engine as _Engine
from sqlalchemy.orm import Session as _Session

_init_lock = _Lock()
_initialized = False

global g_session
g_session: _Session

global g_engine
g_engine: _Engine


def init():
    global _initialized
    with _init_lock:
        if _initialized:
            return

        import os
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # Load DB path
        global DPDKNET_DB_PATH
        DPDKNET_DB_PATH = os.getenv('DPDKNET_DB_PATH', '/opt/dpdknet/db/dpdknet.db')

        # Ensure directory exists
        os.makedirs(os.path.dirname(DPDKNET_DB_PATH), exist_ok=True)

        # Create SQLAlchemy engine
        global g_engine
        g_engine = create_engine(f'sqlite:///{DPDKNET_DB_PATH}', echo=False)

        # Create a session
        Session = sessionmaker(bind=g_engine)
        global g_session
        g_session = Session()

        # Create tables if they do not exist
        import dpdknet.db.models.base as base
        import dpdknet.db.models.host as _
        import dpdknet.db.models.ovs as _
        import dpdknet.db.models.link as _

        base.BaseModel.metadata.create_all(g_engine)


init()
