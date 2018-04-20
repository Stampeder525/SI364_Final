"""second migration

Revision ID: 04fdee6405ca
Revises: 
Create Date: 2018-04-19 16:25:00.202404

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '04fdee6405ca'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('songs_albumid_fkey', 'songs', type_='foreignkey')
    op.drop_column('songs', 'genre')
    op.drop_column('songs', 'albumid')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('songs', sa.Column('albumid', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('songs', sa.Column('genre', sa.VARCHAR(length=64), autoincrement=False, nullable=True))
    op.create_foreign_key('songs_albumid_fkey', 'songs', 'albums', ['albumid'], ['id'])
    # ### end Alembic commands ###
