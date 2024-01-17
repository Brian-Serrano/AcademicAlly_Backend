"""First Migration.

Revision ID: fe0a5543239e
Revises: 
Create Date: 2024-01-13 21:49:07.791602

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fe0a5543239e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('primary_learning_pattern', sa.String(), nullable=False, server_default="NA"))
        batch_op.add_column(sa.Column('secondary_learning_pattern', sa.String(), nullable=False, server_default="NA"))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('secondary_learning_pattern')
        batch_op.drop_column('primary_learning_pattern')

    # ### end Alembic commands ###
