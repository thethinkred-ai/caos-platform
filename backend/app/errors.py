"""Machine-readable domain errors (Track E2).

HTTPException stays for transport-level errors; DomainError carries a
stable `code` for the frontend on top of the human-readable `detail`,
per critique part two (Step 27): INVALID_STATE_TRANSITION,
RESULT_ALREADY_VERIFIED, FORBIDDEN_SCOPE, etc.
"""


class DomainError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
ACHIEVEMENT_REQUIRES_VERIFIED_RESULT = "ACHIEVEMENT_REQUIRES_VERIFIED_RESULT"
SELF_VERIFICATION_FORBIDDEN = "SELF_VERIFICATION_FORBIDDEN"
RESULT_ALREADY_VERIFIED = "RESULT_ALREADY_VERIFIED"
FORBIDDEN_SCOPE = "FORBIDDEN_SCOPE"
CHALLENGE_ALREADY_RESOLVED = "CHALLENGE_ALREADY_RESOLVED"
