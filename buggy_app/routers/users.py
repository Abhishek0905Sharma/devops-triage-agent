from fastapi import APIRouter, HTTPException, status
from buggy_app.models import User, UserCreate, UserUpdate
from buggy_app.db import USERS_DB
import buggy_app.services.users as user_service

router = APIRouter()

@router.get("/users", response_model=list[User])
def list_users():
    return list(USERS_DB.values())

@router.get("/users/{user_id}", response_model=User)
def get_user(user_id: int):
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/users/{user_id}/bio")
def get_user_bio(user_id: int):
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # [BUG 2]: Missing Null Check
    # If user.profile is None, accessing user.profile.bio will raise
    # AttributeError: 'NoneType' object has no attribute 'bio'.
    return {"username": user.username, "bio": user.profile.bio}

@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate):
    try:
        new_user = user_service.create_user(user_data)
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/users/{user_id}", response_model=User)
def update_user(user_id: int, update_data: UserUpdate):
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # This calls update_user service which raises NameError due to Bug 1
    updated_user = user_service.update_user(user_id, update_data)
    return updated_user
