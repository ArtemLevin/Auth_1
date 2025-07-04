"""Partition login_history by login_at

Revision ID: 268c5333e9fd
Revises: 70280b8d5b55
Create Date: 2025-07-03 12:14:37.862013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '268c5333e9fd'
down_revision: Union[str, None] = '70280b8d5b55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE login_history RENAME TO login_history_old;")

    op.execute("""
    CREATE TABLE login_history (
        id        UUID,
        user_id   UUID NOT NULL,
        login_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        ip_address VARCHAR(50),
        user_agent VARCHAR(255),
        CONSTRAINT fk_login_history_user FOREIGN KEY (user_id)
          REFERENCES users(id) ON DELETE CASCADE,
        PRIMARY KEY (id, login_at)
    ) PARTITION BY RANGE (login_at);
    """)

    op.execute("""
        CREATE TABLE login_history_2025_06 PARTITION OF login_history
          FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
    """)
    op.execute("""
         CREATE TABLE login_history_2025_07 PARTITION OF login_history
          FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');
    """)

    op.execute("""
    INSERT INTO login_history (id, user_id, login_at, ip_address, user_agent)
      SELECT id, user_id, login_at, ip_address, user_agent
      FROM login_history_old;
    """)

    op.execute("DROP TABLE login_history_old;")

    op.create_index(
        "ix_login_history_login_at", "login_history", ["login_at"]
    )
    op.create_index(
        "ix_login_history_user_id", "login_history", ["user_id"]
    )

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_login_history_login_at;")
    op.execute("DROP INDEX IF EXISTS ix_login_history_user_id;")
    op.execute("DROP TABLE login_history;")
    op.execute("ALTER TABLE login_history_old RENAME TO login_history;")
