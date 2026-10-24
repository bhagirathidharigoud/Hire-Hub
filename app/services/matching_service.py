class MatchingService:
    @staticmethod
    def match_score(candidate_skills, job_skills, candidate_location=None, job_location=None):
        candidate_skill_map = {
            str(skill).strip().lower(): str(skill).strip()
            for skill in (candidate_skills or [])
            if str(skill).strip()
        }
        job_skill_map = {
            str(skill).strip().lower(): str(skill).strip()
            for skill in (job_skills or [])
            if str(skill).strip()
        }
        matched_keys = candidate_skill_map.keys() & job_skill_map.keys()
        missing_keys = job_skill_map.keys() - candidate_skill_map.keys()
        matched = sorted(job_skill_map[key] for key in matched_keys)
        missing = sorted(job_skill_map[key] for key in missing_keys)
        score = 0 if not job_skill_map else round((len(matched) / len(job_skill_map)) * 100)
        if candidate_location and job_location and candidate_location.casefold() == job_location.casefold():
            score = min(100, score + 10)
        return {"score": score, "matched_skills": matched, "missing_skills": missing}

    @classmethod
    def recommend_jobs(cls, candidate, jobs, excluded_job_ids=None, limit=6):
        excluded_job_ids = set(excluded_job_ids or [])
        recommendations = []
        for job in jobs:
            if job.get("status") != "OPEN" or job.get("_id") in excluded_job_ids:
                continue
            match = cls.match_score(
                candidate.get("skills", []),
                job.get("skills", []),
                candidate.get("location"),
                job.get("location"),
            )
            if match["score"] == 0:
                continue
            recommendations.append({**job, "match": match})
        recommendations.sort(
            key=lambda job: (
                job["match"]["score"],
                job.get("posted_date", job.get("created_at", "")),
            ),
            reverse=True,
        )
        return recommendations[:limit]

    def recommend_for_candidate(self, candidate_id, limit=6):
        from app.repositories.application_repository import ApplicationRepository
        from app.repositories.job_repository import JobRepository
        from app.repositories.user_repository import UserRepository

        candidate = UserRepository().find_one({"_id": candidate_id})
        if not candidate or candidate.get("role") != "CANDIDATE":
            return []
        applications = ApplicationRepository().find_all({"candidate_id": candidate_id})
        excluded_job_ids = {application.get("job_id") for application in applications}
        return self.recommend_jobs(
            candidate,
            JobRepository().find_all({"status": "OPEN"}),
            excluded_job_ids,
            limit,
        )
