"""Add nullable captured instructional revisions without rewriting old sessions."""

from alembic import op
from src.core.services.schema_migrations import reconcile_connection

revision = "20261004_learning_snapshots"
down_revision = "20261004_reconcile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    reconcile_connection(op.get_bind())


def downgrade() -> None:
    raise RuntimeError("Restore the pre-upgrade backup; captured history must not be dropped automatically")
