"""Add nullable help request replay identities and source revision context."""

from alembic import op
from src.core.services.schema_migrations import reconcile_connection

revision = "20261004_request_context"
down_revision = "20261004_learning_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    reconcile_connection(op.get_bind())


def downgrade() -> None:
    raise RuntimeError("Restore the verified pre-upgrade backup; do not discard help request history")
