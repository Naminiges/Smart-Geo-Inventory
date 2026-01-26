"""remove user profile_image

Revision ID: remove_profile_image
Revises: add_user_profile_image
Create Date: 2026-01-26 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_user_profile_image'
down_revision = 'add_user_profile_image'
branch_labels = None
depends_on = None


def upgrade():
    # Remove profile_image column from users table
    op.drop_column('users', 'profile_image')


def downgrade():
    # Add back profile_image column if rollback is needed
    op.add_column('users',
        sa.Column('profile_image', sa.String(length=255), nullable=True)
    )
