"""added rating to songs

Revision ID: c85aabc5459c
Revises: e68348ad6a48
Create Date: 2018-04-19 17:29:29.490822

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c85aabc5459c'
down_revision = 'e68348ad6a48'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('songs', sa.Column('rating', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('songs', 'rating')
    # ### end Alembic commands ###