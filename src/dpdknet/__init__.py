from threading import Lock as _Lock

from sqlalchemy.orm import Session as _Session

_init_lock = _Lock()
_initialized = False

global g_session
g_session: _Session

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
        engine = create_engine(f"sqlite:///{DPDKNET_DB_PATH}", echo=True)

        # Create a session
        Session = sessionmaker(bind=engine)
        global g_session
        g_session = Session()

        # Create tables if they do not exist
        from dpdknet.db.models.base import Base
        from dpdknet.db.models.ovs import OvsBridgeModel, OvsPortModel
        Base.metadata.create_all(engine)

init()

