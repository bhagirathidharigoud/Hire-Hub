from __future__ import annotations

import re
from uuid import uuid4

from flask import current_app, has_app_context


class BaseRepository:
    collection_name = "items"

    def _mongo_collection(self):
        if not has_app_context():
            return None
        mongo_db = current_app.extensions.get("mongo_db")
        if mongo_db is None:
            return None
        return mongo_db[self.collection_name]

    def _normalize_document(self, document):
        if document is None:
            return None
        normalized = dict(document)
        if "_id" in normalized and not isinstance(normalized["_id"], str):
            normalized["_id"] = str(normalized["_id"])
        return normalized

    def _collection(self):
        store = current_app.extensions.setdefault("memory_store", {})
        store.setdefault(self.collection_name, [])
        return store[self.collection_name]

    def _matches(self, item, key, value):
        if key == "$or":
            return any(
                self._matches(item, clause_key, clause_value)
                for clause in value
                for clause_key, clause_value in clause.items()
            )
        if isinstance(value, dict):
            if "$regex" in value:
                pattern = value["$regex"]
                flags = value.get("$options", "")
                return bool(re.search(pattern, str(item.get(key, "")), flags=re.I if "i" in flags else 0))
            if "$in" in value:
                item_value = item.get(key)
                if isinstance(item_value, (list, tuple, set)):
                    return bool(set(item_value) & set(value["$in"]))
                return item_value in value["$in"]
            if "$gte" in value:
                return (item.get(key) or 0) >= value["$gte"]
            if "$lte" in value:
                return (item.get(key) or 0) <= value["$lte"]
            if "$gt" in value:
                return (item.get(key) or 0) > value["$gt"]
            if "$lt" in value:
                return (item.get(key) or 0) < value["$lt"]
            if "$exists" in value:
                exists = key in item or item.get(key) is not None
                return exists == bool(value["$exists"])
            return item.get(key) == value
        return item.get(key) == value

    def insert_one(self, document):
        document = dict(document)
        document.setdefault("_id", str(uuid4()))

        mongo_collection = self._mongo_collection()
        if mongo_collection is not None:
            mongo_collection.insert_one(document)
            return str(document["_id"])

        self._collection().append(document)
        return document["_id"]

    def find_all(self, filters=None, sort=None):
        mongo_collection = self._mongo_collection()
        if mongo_collection is not None:
            docs = list(mongo_collection.find(filters or {}))
            if sort:
                reverse = bool(sort[1]) if len(sort) > 1 else False
                docs = sorted(docs, key=lambda item: str(item.get(sort[0], "")), reverse=reverse)
            return [self._normalize_document(doc) for doc in docs]

        items = list(self._collection())
        filters = filters or {}
        if filters:
            items = [
                item for item in items
                if all(self._matches(item, key, value) for key, value in filters.items())
            ]
        if sort:
            reverse = bool(sort[1]) if len(sort) > 1 else False
            items = sorted(items, key=lambda item: item.get(sort[0], ""), reverse=reverse)
        return items

    def find_one(self, filters=None):
        mongo_collection = self._mongo_collection()
        if mongo_collection is not None:
            return self._normalize_document(mongo_collection.find_one(filters or {}))

        filters = filters or {}
        for item in self._collection():
            if all(self._matches(item, key, value) for key, value in filters.items()):
                return item
        return None

    def update_one(self, filters, updates):
        mongo_collection = self._mongo_collection()
        if mongo_collection is not None:
            mongo_collection.update_one(filters, {"$set": updates})
            return self.find_one(filters)

        for item in self._collection():
            if all(self._matches(item, key, value) for key, value in filters.items()):
                item.update(updates)
                return item
        return None

    def delete_one(self, filters):
        mongo_collection = self._mongo_collection()
        if mongo_collection is not None:
            result = mongo_collection.delete_one(filters)
            return result.deleted_count > 0

        collection = self._collection()
        original = len(collection)
        collection[:] = [
            item for item in collection
            if not all(self._matches(item, key, value) for key, value in filters.items())
        ]
        return len(collection) != original

    def count_documents(self, filters=None):
        mongo_collection = self._mongo_collection()
        if mongo_collection is not None:
            return mongo_collection.count_documents(filters or {})
        return len(self.find_all(filters or {}))
