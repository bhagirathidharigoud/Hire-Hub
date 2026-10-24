from app.repositories.base_repository import BaseRepository


class InterviewRepository(BaseRepository):
    collection_name = "interviews"

    def find_by_candidate(self, candidate_id):
        return self.find_all({"candidate_id": candidate_id})
