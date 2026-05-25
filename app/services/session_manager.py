import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import pandas as pd

from app.core.config import settings


class SessionData:
    def __init__(self, df: pd.DataFrame, filename: str) -> None:
        self.df = df
        self.filename = filename
        self.created_at = datetime.now(tz=timezone.utc)
        self.expires_at = self.created_at + timedelta(minutes=settings.SESSION_TTL_MINUTES)

    def is_expired(self) -> bool:
        return datetime.now(tz=timezone.utc) > self.expires_at


class SessionManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionData] = {}

    def create(self, df: pd.DataFrame, filename: str) -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = SessionData(df, filename)
        self._cleanup_expired()
        return session_id

    def get(self, session_id: str) -> Optional[SessionData]:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.is_expired():
            del self._sessions[session_id]
            return None
        return session

    def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def _cleanup_expired(self) -> None:
        expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
        for sid in expired:
            del self._sessions[sid]


session_manager = SessionManager()
