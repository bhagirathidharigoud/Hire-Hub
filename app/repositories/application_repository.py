from app.repositories.base_repository import BaseRepository


class ApplicationRepository(BaseRepository):
    collection_name = "applications"

    def find_by_candidate(self, candidate_id):
        return self.find_all({"candidate_id": candidate_id})

    def find_by_job(self, job_id):
        return self.find_all({"job_id": job_id})

    def find_by_candidate_and_job(self, candidate_id, job_id):
        return self.find_one({"candidate_id": candidate_id, "job_id": job_id})
