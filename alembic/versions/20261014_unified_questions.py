"""Add durable question threads and the installation-wide AI selection."""
from alembic import op
from src.core.services.schema_migrations import reconcile_connection

revision = "20261014_unified_questions"
down_revision = "20261004_request_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    reconcile_connection(op.get_bind())


def downgrade() -> None:
    raise RuntimeError("Restore the verified pre-upgrade backup; do not discard question history")
