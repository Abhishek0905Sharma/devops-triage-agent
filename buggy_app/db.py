from datetime import datetime
from buggy_app.models import User, Profile

# Mock database dictionary storing users by ID
USERS_DB: dict[int, User] = {
    1: User(
        id=1,
        username="alice",
        email="alice@example.com",
        is_active=True,
        created_at=datetime(2023, 1, 15),
        profile=Profile(bio="Senior DevOps Engineer & Python enthusiast.", website="https://alice.dev")
    ),
    2: User(
        id=2,
        username="bob",
        email="bob@example.com",
        is_active=True,
        created_at=datetime(2025, 12, 1),  # Less than 365 days from now
        profile=None  # Triggers Bug 2 when accessing profile.bio
    ),
    3: User(
        id=3,
        username="charlie",
        email="charlie@example.com",
        is_active=False,
        created_at=datetime(2022, 6, 20),
        profile=Profile(bio="Security specialist. I break things so you don't have to.", website="https://charlie.security")
    )
}
