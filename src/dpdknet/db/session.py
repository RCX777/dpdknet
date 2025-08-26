import os
import threading

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from dpdknet.db.models.base import BaseModel
from dpdknet.db.models.ovs import *
from dpdknet.db.models.host import *
from dpdknet.db.models.link import *

global g_engine
g_engine: Engine

global g_session
g_session: Session

_init_lock = threading.Lock()
_initialized = False

def init_session():
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return

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

    BaseModel.metadata.create_all(g_engine)

def clean_db():
    g_session.commit()
    BaseModel.metadata.drop_all(g_engine)
    BaseModel.metadata.create_all(g_engine)

init_session()

