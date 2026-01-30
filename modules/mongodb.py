from typing import Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo import UpdateOne
from pymongo.results import BulkWriteResult, UpdateResult

import constants


class Collection:
    def __init__(self, db: str, collection: str):
        self.db_name = db
        self.collection_name = collection
        self._client: AsyncIOMotorClient | None = None
        self._collection: AsyncIOMotorCollection | None = None

    async def get_client(self) -> AsyncIOMotorClient:
        if self._client is None:
            self._client = AsyncIOMotorClient(constants.MONGODB_URI)
        return self._client

    async def get_collection(self) -> AsyncIOMotorCollection:
        if self._collection is None:
            client = await self.get_client()
            self._collection = client[self.db_name][self.collection_name]
        return self._collection

    def close(self):
        if self._client is not None:
            self._client.close()
            self._client = None
            self._collection = None

    async def update_one(
        self,
        data: dict[str, Any],
        query: dict[str, Any] | None = None,
        upsert: bool = False,
    ):
        if query is None and not data.get("_id"):
            raise ValueError("Query is required when data does not have an _id")
        if query is None:
            query = {"_id": data["_id"]}
        collection = await self.get_collection()
        return await collection.update_one(query, {"$set": data}, upsert=upsert)

    async def insert(
        self, *documents: dict[str, Any]
    ) -> UpdateResult | BulkWriteResult:
        if len(documents) == 1:
            return await self.update_one(documents[0])
        collection = await self.get_collection()
        operations = [
            UpdateOne({"_id": document["_id"]}, {"$set": document}, upsert=True)
            for document in documents
        ]
        return await collection.bulk_write(operations)

    async def get(
        self, query: dict[str, Any], projection: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        collection = await self.get_collection()
        return await collection.find_one(query, projection=projection)

    async def get_many(
        self,
        query: dict[str, Any],
        projection: dict[str, Any] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        collection = await self.get_collection()
        return (
            await collection.find(query, projection=projection)
            .limit(limit)
            .to_list(length=limit)
        )
