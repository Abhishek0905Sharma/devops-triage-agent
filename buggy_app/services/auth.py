import hashlib
import uuid
from datetime import datetime, timedelta

SESSION_EXPIRY_HOURS = 24
active_sessions: dict[str, dict] = {}

def hash_password(password: str, salt: str | None = None) -> str:
    """Returns a SHA-256 hashed password with an optional salt."""
    if not salt:
        salt = "devops_triage_default_salt"
    salted = password + salt
    return hashlib.sha256(salted.encode('utf-8')).hexdigest()

def create_session(user_id: int) -> str:
    """Creates a mock session token for the user."""
    token = str(uuid.uuid4())
    expiry = datetime.utcnow() + timedelta(hours=SESSION_EXPIRY_HOURS)
    active_sessions[token] = {
        "user_id": user_id,
        "expires_at": expiry
    }
    return token

def validate_session(token: str) -> int | None:
    """Validates the session token, returning the user_id if valid, else None."""
    session = active_sessions.get(token)
    if not session:
        return None
        
    if datetime.utcnow() > session["expires_at"]:
        active_sessions.pop(token, None)
        return None
        
    return session["user_id"]
