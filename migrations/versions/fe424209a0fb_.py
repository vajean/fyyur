"""empty message

Revision ID: fe424209a0fb
Revises: c61d9a119282
Create Date: 2020-04-26 20:01:24.982414

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fe424209a0fb'
down_revision = 'c61d9a119282'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('Venue', 'genres')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Venue', sa.Column('genres', postgresql.ARRAY(sa.VARCHAR(length=30)), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
