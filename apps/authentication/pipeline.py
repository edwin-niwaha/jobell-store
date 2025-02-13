import logging
from .models import Profile

logger = logging.getLogger(__name__)

def create_profile(backend, user, response, *args, **kwargs):
    """Create a profile for the user if it does not exist."""
    logger.info(f"Running create_profile for user: {user}")

    if not hasattr(user, "profile"):
        Profile.objects.create(user=user)
        logger.info(f"Profile created for user: {user}")

    # Debugging: Print social auth UID
    uid = kwargs.get("uid", None)
    logger.info(f"UID from social auth: {uid}")

    # Assign a default role
    user.profile.role = "guest"  
    user.profile.save()
    logger.info(f"Profile updated for user: {user}")
