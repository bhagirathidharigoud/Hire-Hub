from pymongo import MongoClient


def init_extensions(app):
    if not app.config.get("USE_MONGO", True):
        if not app.testing:
            raise RuntimeError("MongoDB is required outside the testing configuration")
        app.extensions.setdefault("memory_store", {})
        app.extensions["mongo_db"] = None
        return
    uri = app.config.get("MONGO_URI")
    db_name = app.config.get("MONGO_DATABASE")
    client = MongoClient(uri, serverSelectionTimeoutMS=2000)
    try:
        client.admin.command("ping")
        mongo_db = client[db_name]
        mongo_db.users.create_index("email", unique=True)
        mongo_db.applications.create_index(
            [("candidate_id", 1), ("job_id", 1)],
            unique=True,
        )
        app.extensions["mongo_db"] = mongo_db
    except Exception as exc:
        app.extensions["mongo_db"] = None
        client.close()
        raise RuntimeError("MongoDB is required but could not be reached") from exc
