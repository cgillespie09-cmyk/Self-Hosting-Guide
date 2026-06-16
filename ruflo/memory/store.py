import asyncio
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

# Try aiosqlite for true async; fall back to thread-executor with sqlite3
try:
    import aiosqlite
    _HAVE_AIOSQLITE = True
except ImportError:
    _HAVE_AIOSQLITE = False


_CREATE_MEMORIES = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tags TEXT
)
"""

_CREATE_TASK_HISTORY = """
CREATE TABLE IF NOT EXISTS task_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task TEXT NOT NULL,
    agent_used TEXT NOT NULL,
    success_score REAL NOT NULL,
    latency_ms REAL NOT NULL,
    tokens_used INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_CREATE_ROUTE_WEIGHTS = """
CREATE TABLE IF NOT EXISTS route_weights (
    agent_name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 5.0,
    attempts INTEGER NOT NULL DEFAULT 0,
    successes INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (agent_name, task_type)
)
"""


class MemoryStore:
    def __init__(self, db_path: str = "~/.ruflo/memory.db"):
        self.db_path = str(Path(db_path).expanduser())
        self._aio_conn = None
        self._sync_conn: Optional[sqlite3.Connection] = None

    def _ensure_dir(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Initialization
    # ------------------------------------------------------------------ #

    async def initialize(self):
        self._ensure_dir()
        if _HAVE_AIOSQLITE:
            await self._init_aiosqlite()
        else:
            await self._run_sync(self._init_sync)

    async def _init_aiosqlite(self):
        self._aio_conn = await aiosqlite.connect(self.db_path)
        await self._aio_conn.execute(_CREATE_MEMORIES)
        await self._aio_conn.execute(_CREATE_TASK_HISTORY)
        await self._aio_conn.execute(_CREATE_ROUTE_WEIGHTS)
        await self._aio_conn.commit()

    def _init_sync(self):
        conn = self._get_sync_conn()
        conn.execute(_CREATE_MEMORIES)
        conn.execute(_CREATE_TASK_HISTORY)
        conn.execute(_CREATE_ROUTE_WEIGHTS)
        conn.commit()

    def _get_sync_conn(self) -> sqlite3.Connection:
        if self._sync_conn is None:
            self._sync_conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._sync_conn.row_factory = sqlite3.Row
        return self._sync_conn

    async def _run_sync(self, fn, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, fn, *args)

    # ------------------------------------------------------------------ #
    # Execute helpers
    # ------------------------------------------------------------------ #

    async def _execute(self, sql: str, params: tuple = ()):
        if _HAVE_AIOSQLITE and self._aio_conn:
            await self._aio_conn.execute(sql, params)
            await self._aio_conn.commit()
        else:
            def _do():
                conn = self._get_sync_conn()
                conn.execute(sql, params)
                conn.commit()
            await self._run_sync(_do)

    async def _fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        if _HAVE_AIOSQLITE and self._aio_conn:
            async with self._aio_conn.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                cols = [d[0] for d in cursor.description]
                return [dict(zip(cols, row)) for row in rows]
        else:
            def _do():
                conn = self._get_sync_conn()
                cur = conn.execute(sql, params)
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
            return await self._run_sync(_do)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tags: Optional[list[str]] = None,
    ):
        tags_str = json.dumps(tags) if tags else None
        await self._execute(
            "INSERT INTO memories (session_id, role, content, tags) VALUES (?, ?, ?, ?)",
            (session_id, role, content, tags_str),
        )

    async def get_context(self, session_id: str, limit: int = 20) -> list[dict]:
        rows = await self._fetchall(
            """
            SELECT role, content, created_at FROM memories
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        )
        # Return in chronological order
        return list(reversed(rows))

    async def log_task_result(
        self,
        task: str,
        agent_used: str,
        success_score: float,
        latency_ms: float,
        tokens_used: int,
    ):
        await self._execute(
            """
            INSERT INTO task_history (task, agent_used, success_score, latency_ms, tokens_used)
            VALUES (?, ?, ?, ?, ?)
            """,
            (task, agent_used, success_score, latency_ms, tokens_used),
        )

    async def get_route_weights(self, task_type: str) -> dict[str, dict]:
        rows = await self._fetchall(
            "SELECT agent_name, weight, attempts, successes FROM route_weights WHERE task_type = ?",
            (task_type,),
        )
        return {
            row["agent_name"]: {
                "weight": row["weight"],
                "attempts": row["attempts"],
                "successes": row["successes"],
            }
            for row in rows
        }

    async def update_route_weight(
        self, agent_name: str, task_type: str, success: bool
    ):
        # Check if row exists
        existing = await self._fetchall(
            "SELECT weight, attempts, successes FROM route_weights WHERE agent_name = ? AND task_type = ?",
            (agent_name, task_type),
        )

        if not existing:
            weight = 6.0 if success else 4.0
            await self._execute(
                """
                INSERT INTO route_weights (agent_name, task_type, weight, attempts, successes, updated_at)
                VALUES (?, ?, ?, 1, ?, CURRENT_TIMESTAMP)
                """,
                (agent_name, task_type, weight, 1 if success else 0),
            )
        else:
            row = existing[0]
            new_attempts = row["attempts"] + 1
            new_successes = row["successes"] + (1 if success else 0)
            # Exponential moving average blended with success rate
            success_rate = new_successes / max(new_attempts, 1)
            new_weight = 0.8 * row["weight"] + 0.2 * (success_rate * 10.0)
            await self._execute(
                """
                UPDATE route_weights
                SET weight = ?, attempts = ?, successes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE agent_name = ? AND task_type = ?
                """,
                (new_weight, new_attempts, new_successes, agent_name, task_type),
            )

    async def get_stats(self) -> list[dict]:
        rows = await self._fetchall(
            """
            SELECT
                agent_used,
                COUNT(*) as total_tasks,
                AVG(success_score) as avg_score,
                AVG(latency_ms) as avg_latency_ms,
                SUM(tokens_used) as total_tokens,
                SUM(CASE WHEN success_score >= 6.0 THEN 1 ELSE 0 END) as successes
            FROM task_history
            GROUP BY agent_used
            ORDER BY avg_score DESC
            """,
            (),
        )
        return list(rows)

    async def get_recent_failures(self, agent_name: str, limit: int = 5) -> list[dict]:
        rows = await self._fetchall(
            """
            SELECT task, success_score, created_at FROM task_history
            WHERE agent_used = ? AND success_score < 6.0
            ORDER BY id DESC
            LIMIT ?
            """,
            (agent_name, limit),
        )
        return list(rows)

    async def close(self):
        if _HAVE_AIOSQLITE and self._aio_conn:
            await self._aio_conn.close()
            self._aio_conn = None
        if self._sync_conn:
            self._sync_conn.close()
            self._sync_conn = None
