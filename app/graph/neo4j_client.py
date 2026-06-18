import asyncio
import logging
from typing import Any

from neo4j import AsyncGraphDatabase
from neo4j.exceptions import SessionExpired, ServiceUnavailable, TransientError

from app.core.config import Settings
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        if settings.allow_mock_services:
            self.driver = None
        else:
            self.driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password),
                connection_timeout=settings.neo4j_connection_timeout_seconds,
                max_connection_lifetime=settings.neo4j_max_connection_lifetime_seconds,
                max_connection_pool_size=settings.neo4j_max_connection_pool_size,
                connection_acquisition_timeout=settings.neo4j_connection_acquisition_timeout_seconds,
                keep_alive=True,
            )

    async def close(self) -> None:
        if self.driver:
            await self.driver.close()

    async def health(self) -> bool:
        if self.driver is None:
            return True
        try:
            await self.driver.verify_connectivity()
            return True
        except Exception:
            return False

    async def read(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if self.driver is None:
            return []
        normalized = query.strip().upper()
        forbidden = (
            " CREATE ",
            " MERGE ",
            " DELETE ",
            " DETACH ",
            " SET ",
            " REMOVE ",
            " DROP ",
            " CALL DBMS",
        )
        padded = f" {normalized} "
        if any(token in padded for token in forbidden):
            raise AppError("FORBIDDEN", "Query graf write tidak diizinkan pada jalur retrieval.", 403)

        attempts = 0
        base_delay = self.settings.neo4j_retry_base_delay_ms / 1000.0
        while True:
            attempts += 1
            try:
                async with self.driver.session(database=self.settings.neo4j_database) as session:
                    # Use managed read transaction which has built-in retry logic
                    return await session.execute_read(self._execute_query, query, parameters or {})
            except (SessionExpired, ServiceUnavailable, TransientError, ConnectionResetError) as exc:
                if attempts <= self.settings.neo4j_max_retry_attempts:
                    await asyncio.sleep(base_delay * (2 ** (attempts - 1)))
                    continue
                self._handle_exception(exc, query, parameters)
            except Exception as exc:
                self._handle_exception(exc, query, parameters)

    async def write(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if self.driver is None:
            return []
        async with self.driver.session(database=self.settings.neo4j_database) as session:
            return await session.execute_write(self._execute_query, query, parameters or {})

    async def _execute_query(self, tx, query: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        result = await tx.run(query, parameters, timeout=self.settings.neo4j_query_timeout_seconds)
        return [record.data() async for record in result]

    def _handle_exception(self, exc: Exception, query: str, parameters: dict[str, Any] | None) -> None:
        details = {
            "exception": type(exc).__name__,
            "reason": str(exc)[:2000],
            "database": self.settings.neo4j_database,
            "query_preview": query.strip()[:1000],
            "parameters": parameters or {},
        }
        logger.exception(
            "neo4j_query_failed",
            extra={
                "error_code": "NEO4J_UNAVAILABLE",
                "error_details": details,
                "stage": "neo4j_retrieval",
            },
        )
        raise AppError(
            code="NEO4J_UNAVAILABLE",
            message="Query knowledge graph gagal.",
            status_code=503,
            details=details,
        ) from exc
