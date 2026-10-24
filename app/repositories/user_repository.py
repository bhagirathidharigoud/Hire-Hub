from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):
    collection_name = "users"

    def create_user(self, user_data):
        return self.insert_one(user_data)

    def find_by_email(self, email):
        return self.find_one({"email": email})

    def find_by_role(self, role):
        return self.find_all({"role": role})
