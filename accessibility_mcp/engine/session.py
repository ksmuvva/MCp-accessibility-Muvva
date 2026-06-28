"""Stateful interactive browser sessions for auditing real user journeys.

Each session owns a long-lived Chromium context + page that survives across MCP
tool calls, so an agent can navigate, log in, click and fill, then audit the
resulting state. Sessions are bounded and can be closed explicitly.
"""

from __future__ import annotations

import uuid

from accessibility_mcp.engine.browser import BrowserSession, apply_steps


class InteractiveSession:
    """A single persistent browser context + page."""

    def __init__(self, session_id: str) -> None:
        self.id = session_id
        self._browser = BrowserSession()
        self.context = None
        self.page = None

    async def start(self) -> None:
        await self._browser.start()
        self.context, self.page = await self._browser.new_persistent_page()

    async def close(self) -> None:
        await self._browser.close()
        self.context = None
        self.page = None


class SessionManager:
    """Tracks active interactive sessions, keyed by id, with a bounded count."""

    def __init__(self, max_sessions: int = 10) -> None:
        self._sessions: dict[str, InteractiveSession] = {}
        self._max = max_sessions

    async def open(self) -> InteractiveSession:
        if len(self._sessions) >= self._max:
            # Evict the oldest session to stay bounded.
            oldest = next(iter(self._sessions))
            await self.close(oldest)
        session_id = uuid.uuid4().hex[:12]
        session = InteractiveSession(session_id)
        await session.start()
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> InteractiveSession | None:
        return self._sessions.get(session_id)

    async def close(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return False
        await session.close()
        return True

    async def close_all(self) -> None:
        for session_id in list(self._sessions):
            await self.close(session_id)

    @property
    def count(self) -> int:
        return len(self._sessions)


# Module-level singleton used by the MCP server.
manager = SessionManager()


async def apply_session_steps(session: InteractiveSession, steps: list[dict] | None) -> None:
    await apply_steps(session.page, steps)
