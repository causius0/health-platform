"""symptom checkins

Revision ID: 9c77a92421d1
Revises: a24b85aac576
Create Date: 2026-09-09 10:32:32.403882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9c77a92421d1'
down_revision: Union[str, None] = 'a24b85aac576'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'symptom_checkins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('taken_on', sa.Date(), nullable=False),
        sa.Column('answers', sa.Text(), nullable=False),
        sa.Column('tier', sa.String(length=12), nullable=False),
        sa.Column('advice', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_symptom_checkins_patient_id', 'symptom_checkins', ['patient_id'])
    op.create_index('ix_symptom_checkins_taken_on', 'symptom_checkins', ['taken_on'])


def downgrade() -> None:
    op.drop_index('ix_symptom_checkins_taken_on', table_name='symptom_checkins')
    op.drop_index('ix_symptom_checkins_patient_id', table_name='symptom_checkins')
    op.drop_table('symptom_checkins')
