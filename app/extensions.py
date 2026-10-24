from pymongo import MongoClient


def init_extensions(app):
    app.extensions.setdefault("memory_store", {})
    if not app.config.get("USE_MONGO", True):
        app.extensions["mongo_db"] = None
        return
    uri = app.config.get("MONGO_URI")
    db_name = app.config.get("MONGO_DATABASE")
    client = MongoClient(uri, serverSelectionTimeoutMS=2000)
    try:
        client.admin.command("ping")
        app.extensions["mongo_db"] = client[db_name]
    except Exception as exc:
        app.extensions["mongo_db"] = None
        app.logger.warning(
            "MongoDB is unavailable; using in-memory storage for this process: %s",
            exc,
        )
        if app.config.get("MONGO_REQUIRED"):
            client.close()
            raise RuntimeError("MongoDB is required but could not be reached") from exc
