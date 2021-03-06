"""new fields in user model

Revision ID: 470ad871bbde
Revises: f33e47ee72a1
Create Date: 2018-11-19 07:21:12.588320

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '470ad871bbde'
down_revision = 'f33e47ee72a1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('about_me', sa.String(length=140), nullable=True))
    op.add_column('user', sa.Column('last_seen', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'last_seen')
    op.drop_column('user', 'about_me')
    # ### end Alembic commands ###
