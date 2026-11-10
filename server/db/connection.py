import os
import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager
import psycopg
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://aw_admin:admin_secure_pass_123@localhost:5432/activitywatch_enterprise"
)

pool: AsyncConnectionPool | None = None

async def init_db_pool():
    global pool
    try:
        pool = AsyncConnectionPool(
            conninfo=DATABASE_URL,
            min_size=2,
            max_size=20,
            open=False
        )
        await pool.open()
        logger.info("Database connection pool initialized successfully.")
    except Exception as e:
        logger.warning(f"Could not connect to PostgreSQL at {DATABASE_URL}: {e}. (Will retry on queries or run in fallback mode)")

async def close_db_pool():
    global pool
    if pool:
        await pool.close()
        logger.info("Database connection pool closed.")

@asynccontextmanager
async def get_db_connection():
    global pool
    if pool is None:
        await init_db_pool()
    if pool:
        async with pool.connection() as conn:
            yield conn
    else:
        raise RuntimeError("Database pool is not available.")
