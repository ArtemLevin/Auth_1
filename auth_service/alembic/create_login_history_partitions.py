from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.execute("ALTER TABLE login_history RENAME TO login_history_old;")

    op.execute("""
    CREATE TABLE login_history (
        id        UUID PRIMARY KEY,
        user_id   UUID NOT NULL,
        login_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        ip_address VARCHAR(50),
        user_agent VARCHAR(255),
        CONSTRAINT fk_login_history_user FOREIGN KEY (user_id)
          REFERENCES users(id) ON DELETE CASCADE
    ) PARTITION BY RANGE (login_at);
    """)

    op.execute("""
    CREATE TABLE login_history_2025_06 PARTITION OF login_history
      FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
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