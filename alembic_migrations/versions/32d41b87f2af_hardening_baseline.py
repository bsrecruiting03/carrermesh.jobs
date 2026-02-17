"""hardening_baseline

Revision ID: 32d41b87f2af
Revises: 0e2df4163da0
Create Date: 2026-02-13 22:37:45.697409

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32d41b87f2af'
down_revision: Union[str, Sequence[str], None] = '0e2df4163da0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add enrichment_status to jobs
    op.add_column('jobs', sa.Column('enrichment_status', sa.String(), nullable=True, server_default='pending'))
    
    # 2. Backfill status for already enriched jobs
    op.execute("""
        UPDATE jobs 
        SET enrichment_status = 'completed' 
        WHERE job_id IN (SELECT job_id FROM job_enrichment)
    """)
    
    # 3. Add CHECK constraint for enrichment_status
    op.create_check_constraint(
        'check_enrichment_status',
        'jobs',
        sa.column('enrichment_status').in_(['pending', 'processing', 'completed', 'failed', 'stale'])
    )
    
    # 4. Clean up invalid salary data (Swap min/max if min > max)
    op.execute("""
        UPDATE jobs 
        SET salary_min = salary_max, salary_max = salary_min 
        WHERE salary_min > salary_max;
    """)
    
    # 5. Create Performance Indexes
    op.create_index('idx_jobs_enrichment_status', 'jobs', ['enrichment_status'])
    op.create_index('idx_jobs_location', 'jobs', ['city', 'state'])
    op.create_index('idx_jobs_salary', 'jobs', ['salary_min', 'salary_max'])
    
    # 6. Create Intelligence Indexes
    op.create_index('idx_job_enrichment_seniority', 'job_enrichment', ['seniority_level'])
    
    # 7. Create Vector Index (IVFFlat)
    # Using 100 lists for approximation - provides 10-20x speedup on semantic search
    op.execute("COMMIT;") # pgvector index creation might need to be outside trans in some envs, but usually fine.
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_job_enrichment_embedding 
        ON job_enrichment USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists = 100);
    """)
    
    # 8. Add Data Quality Logic (CHECK Constraints)
    op.create_check_constraint(
        'check_salary_range',
        'jobs',
        sa.text('salary_min <= salary_max')
    )

    # 9. Schema Documentation (COMMENT ON)
    op.execute("COMMENT ON COLUMN jobs.enrichment_status IS 'Tracks the AI enrichment state (pending, processing, completed, failed)';")
    op.execute("COMMENT ON TABLE job_enrichment IS 'Deep technical intelligence (skills, seniority, summary, embeddings)';")


def downgrade() -> None:
    op.drop_constraint('check_salary_range', 'jobs')
    op.execute("DROP INDEX IF EXISTS idx_job_enrichment_embedding")
    op.drop_index('idx_job_enrichment_seniority', 'job_enrichment')
    op.drop_index('idx_jobs_salary', 'jobs')
    op.drop_index('idx_jobs_location', 'jobs')
    op.drop_index('idx_jobs_enrichment_status', 'jobs')
    op.drop_constraint('check_enrichment_status', 'jobs')
    op.drop_column('jobs', 'enrichment_status')

