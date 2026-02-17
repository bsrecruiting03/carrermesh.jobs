"""hashing_and_trigrams

Revision ID: 19d36dd30aff
Revises: 32d41b87f2af
Create Date: 2026-02-13 22:58:57.994099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '19d36dd30aff'
down_revision: Union[str, Sequence[str], None] = '32d41b87f2af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pg_trgm extension for fuzzy search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    
    # 2. Add description_hash to jobs
    op.add_column('jobs', sa.Column('description_hash', sa.String(), nullable=True))
    op.create_index('idx_jobs_description_hash', 'jobs', ['description_hash'])
    
    # 3. Add fuzzy search indexes (GIN Trigram)
    # Using GIN index for fast partial string and fuzzy matches
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_title_trgm 
        ON jobs USING gin (title gin_trgm_ops);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_company_trgm 
        ON jobs USING gin (company gin_trgm_ops);
    """)

    # 4. Schema Documentation
    op.execute("COMMENT ON COLUMN jobs.description_hash IS 'MD5 hash of job_description to prevent redundant AI processing';")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_jobs_company_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_jobs_title_trgm;")
    op.drop_index('idx_jobs_description_hash', 'jobs')
    op.drop_column('jobs', 'description_hash')
    # We usually don't drop extensions in downgrade unless absolutely sure, 
    # as other features might use them. but for completeness:
    # op.execute("DROP EXTENSION IF EXISTS pg_trgm;")

