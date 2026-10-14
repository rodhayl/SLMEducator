"""One administrator-selected AI configuration for this installation."""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.core.models import AIModelConfiguration, User, UserRole
from src.core.models.models import SharedAIConfiguration


def shared_ai_configuration(db: Session, *, optional: bool = False):
    """Read the singleton or unambiguously adopt one legacy admin configuration.

    Legacy rows remain untouched. Multiple administrator rows require an explicit
    administrator save rather than silently choosing a credential or destination.
    """
    selection = db.get(SharedAIConfiguration, 1)
    if selection:
        config = db.get(AIModelConfiguration, selection.configuration_id)
        if config is None:
            raise HTTPException(409, "The administrator must configure the installation AI")
        return config
    configs = (db.query(AIModelConfiguration).join(User, User.id == AIModelConfiguration.user_id)
               .filter(User.role == UserRole.ADMIN).order_by(AIModelConfiguration.id).all())
    if len(configs) > 1:
        raise HTTPException(409, "Multiple legacy administrator configurations exist; an administrator must explicitly save the shared AI configuration")
    if configs:
        return configs[0]
    if optional:
        return None
    raise HTTPException(409, "The administrator has not configured the installation AI")
