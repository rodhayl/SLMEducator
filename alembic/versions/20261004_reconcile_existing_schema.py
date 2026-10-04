"""Reconcile previously stamped schemas with current non-destructive models.

Unstamped create_all installations must use scripts/recover_database.py upgrade;
that workflow verifies a backup/new copy before marking this baseline.
"""
from alembic import op
from src.core.services.schema_migrations import reconcile_connection

revision = "20261004_reconcile"
down_revision = "7924cdebd9c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing compatible fields on a deliberately migrated installation."""
    reconcile_connection(op.get_bind())


def downgrade() -> None:
    """Recovery uses the verified backup; never guess which legacy fields to drop."""
    raise RuntimeError("Destructive downgrade is unsupported; restore the verified pre-upgrade backup to a new database")
