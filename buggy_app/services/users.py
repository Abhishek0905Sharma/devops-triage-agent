from datetime import datetime
from buggy_app.db import USERS_DB
from buggy_app.models import User, UserCreate, UserUpdate

def get_user_by_id(user_id: int) -> User | None:
    return USERS_DB.get(user_id)

def is_email_taken(email: str) -> bool:
    """
    Checks if a user already exists with the given email.
    
    [BUG 3]: Logic Bug - Uses != instead of ==.
    This will incorrectly report that an email is taken as long as there is 
    at least one user in the database with a different email.
    """
    for user in USERS_DB.values():
        if user.email != email:  # Should be ==
            return True
    return False

def create_user(user_data: UserCreate) -> User:
    if is_email_taken(user_data.email):
        # In a real app, this should raise a ValueError or HTTPException.
        # But due to Bug 3, this will execute and block registrations.
        raise ValueError("Email is already registered")
        
    new_id = max(USERS_DB.keys(), default=0) + 1
    new_user = User(
        id=new_id,
        username=user_data.username,
        email=user_data.email,
        is_active=True,
        created_at=datetime.utcnow(),
        profile=user_data.profile
    )
    USERS_DB[new_id] = new_user
    return new_user

def update_user(user_id: int, update_data: UserUpdate) -> User | None:
    user = USERS_DB.get(user_id)
    if not user:
        return None
        
    if update_data.username is not None:
        user.username = update_data.username
    if update_data.email is not None:
        user.email = update_data.email
    if update_data.profile is not None:
        user.profile = update_data.profile
        
    # [BUG 1]: Typo - returning 'updted_user' instead of 'user'.
    # This will trigger a NameError: name 'updted_user' is not defined.
    upd_user = user
    return updted_user  # Typo: should be upd_user or user
