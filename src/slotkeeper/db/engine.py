from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from slotkeeper.config import Settings

_engine = None
_Session = None

def get_session():
    global _engine, _Session
    if _engine is None:
        url = Settings().DATABASE_URL
        _engine = create_engine(url, pool_pre_ping=True, future=True)
        _Session = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _Session()