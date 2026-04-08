"""
MongoDB async connection using Motor.
Provides a shared database instance for all routes.
"""

from motor.motor_asyncio import AsyncIOMotorClient

from backend.app.config import settings

_client: AsyncIOMotorClient = None


async def connect_db():
    """Initialize the MongoDB connection."""
    global _client
    _client = AsyncIOMotorClient(settings.MONGO_URI)
    # Verify connection
    await _client.admin.command("ping")


async def close_db():
    """Close the MongoDB connection."""
    global _client
    if _client:
        _client.close()


def get_db():
    """Return the database instance."""
    return _client[settings.MONGO_DB_NAME]
