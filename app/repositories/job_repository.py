import re

from app.repositories.base_repository import BaseRepository


class JobRepository(BaseRepository):
    collection_name = "jobs"

    def search(self, **filters):
        query = {}
        for key, value in filters.items():
            if value in (None, "", "all"):
                continue
            if key == "keyword":
                pattern = re.escape(str(value).strip())
                if pattern:
                    query["$or"] = [
                        {field: {"$regex": pattern, "$options": "i"}}
                        for field in ("title", "description", "company_name", "skills")
                    ]
            elif key == "location":
                query[key] = {"$regex": re.escape(str(value).strip()), "$options": "i"}
            elif key == "company":
                query["company_name"] = {"$regex": re.escape(str(value).strip()), "$options": "i"}
            elif key == "skills":
                skills = value if isinstance(value, (list, tuple, set)) else str(value).split(",")
                query["skills"] = {"$in": [str(skill).strip() for skill in skills if str(skill).strip()]}
            elif key == "min_salary":
                query["salary_max"] = {"$gte": int(value)}
            elif key == "max_salary":
                query["salary_min"] = {"$lte": int(value)}
            elif key == "min_experience":
                query["experience_max"] = {"$gte": int(value)}
            elif key == "max_experience":
                query["experience_min"] = {"$lte": int(value)}
            elif key in {"salary_min", "experience_min"}:
                query[key] = {"$gte": int(value)}
            elif key in {"salary_max", "experience_max"}:
                query[key] = {"$lte": int(value)}
            else:
                query[key] = value
        return self.find_all(query)
