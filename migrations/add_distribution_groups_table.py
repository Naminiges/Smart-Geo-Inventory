"""Add distribution_groups table and update distributions table

Revision ID: add_distribution_groups
Revises: add_draft_rejection_fields
Create Date: 2025-01-22 08:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_distribution_groups'
down_revision = 'add_draft_rejection_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Create distribution_groups table
    op.create_table(
        'distribution_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('batch_code', sa.String(length=100), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('unit_id', sa.Integer(), nullable=False),
        sa.Column('is_draft', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('verified_by', sa.Integer(), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_by', sa.Integer(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
        sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['rejected_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('batch_code')
    )

    # Create indexes for distribution_groups
    op.create_index(op.f('ix_distribution_groups_batch_code'), 'distribution_groups', ['batch_code'], unique=True)
    op.create_index(op.f('ix_distribution_groups_is_draft'), 'distribution_groups', ['is_draft'], unique=False)
    op.create_index(op.f('ix_distribution_groups_status'), 'distribution_groups', ['status'], unique=False)

    # Add distribution_group_id column to distributions table
    op.add_column('distributions',
                  sa.Column('distribution_group_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_distributions_distribution_group_id'), 'distributions', ['distribution_group_id'], unique=False)
    op.create_foreign_key('distributions_distribution_group_id_fkey', 'distributions', 'distribution_groups', ['distribution_group_id'], ['id'])


def downgrade():
    # Remove distribution_group_id from distributions
    op.drop_constraint('distributions_distribution_group_id_fkey', 'distributions', type_='foreignkey')
    op.drop_index(op.f('ix_distributions_distribution_group_id'), table_name='distributions')
    op.drop_column('distributions', 'distribution_group_id')

    # Drop distribution_groups table
    op.drop_index(op.f('ix_distribution_groups_status'), table_name='distribution_groups')
    op.drop_index(op.f('ix_distribution_groups_is_draft'), table_name='distribution_groups')
    op.drop_index(op.f('ix_distribution_groups_batch_code'), table_name='distribution_groups')
    op.drop_table('distribution_groups')
