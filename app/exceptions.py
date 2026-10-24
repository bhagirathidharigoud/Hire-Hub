class HireHubError(Exception):
    code = "HIREHUB_ERROR"

    def __init__(self, message, code=None):
        super().__init__(message)
        self.message = message
        self.code = code or self.code


class UserAlreadyExistsError(HireHubError):
    code = "USER_ALREADY_EXISTS"


class InvalidCredentialsError(HireHubError):
    code = "INVALID_CREDENTIALS"


class UserNotFoundError(HireHubError):
    code = "USER_NOT_FOUND"


class UnauthorizedError(HireHubError):
    code = "UNAUTHORIZED"


class JobNotFoundError(HireHubError):
    code = "JOB_NOT_FOUND"


class JobClosedError(HireHubError):
    code = "JOB_CLOSED"


class DuplicateApplicationError(HireHubError):
    code = "DUPLICATE_APPLICATION"


class ApplicationNotFoundError(HireHubError):
    code = "APPLICATION_NOT_FOUND"


class InvalidApplicationStatusError(HireHubError):
    code = "INVALID_APPLICATION_STATUS"


class ResumeUploadError(HireHubError):
    code = "RESUME_UPLOAD_ERROR"


class ValidationError(HireHubError):
    code = "VALIDATION_ERROR"


class UserDeactivatedError(HireHubError):
    code = "USER_DEACTIVATED"
