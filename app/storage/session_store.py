from dataclasses import dataclass
from typing import Dict, Optional
import time

@dataclass
class Entry:
    value: str
    exp: int  # epoch seconds

_store: Dict[str, Entry] = {}

def set_sso(username: str, cookie: str, ttl_seconds: int = 3300) -> None:
    _store[username] = Entry(cookie, int(time.time()) + ttl_seconds)

def get_sso(username: str) -> Optional[str]:
    e = _store.get(username)
    if not e:
        return None
    if e.exp < time.time():
        _store.pop(username, None)
        return None
    return e.value

def clear_sso(username: str) -> None:
    _store.pop(username, None)