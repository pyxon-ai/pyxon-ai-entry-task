import os
import uuid
import tempfile
from dataclasses import dataclass

@dataclass
class AppState:
    workdir: str
    sqlite_path: str
    qdrant_path: str | None

def build_state(persist: bool) -> AppState:
    sid = str(uuid.uuid4())
    base = os.path.join(tempfile.gettempdir(), "pyxon_demo", sid)
    os.makedirs(base, exist_ok=True)
    sqlite_path = os.path.join(base, "meta.db")
    qdrant_path = os.path.join(base, "qdrant") if persist else None
    return AppState(workdir=base, sqlite_path=sqlite_path, qdrant_path=qdrant_path)
