"""empty message

Revision ID: 2d7cb2bea5bb
Revises:
Create Date: 2018-09-20 06:55:49.353375

"""
from alembic import op
import sqlalchemy as sa
from app.models import CategoryType

# revision identifiers, used by Alembic.
revision = '2d7cb2bea5bb'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    categorytype_table = op.create_table('categorytype',
    sa.Column('id', sa.Integer(), nullable=True),
    sa.Column('cattype', sa.String(length=128), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    # ### end Alembic commands ###
    op.bulk_insert(categorytype_table,
    [
        {'id':1, 'cattype':'Home'},
        {'id':2, 'cattype':'Household'},
        {'id':3, 'cattype':'Clothing'},
        {'id':4, 'cattype':'Leisure'},
        {'id':5, 'cattype':'Mobility'},
        {'id':6, 'cattype':'Healthcare'},
        {'id':7, 'cattype':'Holiday'},
        {'id':8, 'cattype':'Education'},
        {'id':9, 'cattype':'Professional'},
        {'id':10, 'cattype':'Social'},
        {'id':11, 'cattype':'Taxes'},
        {'id':12, 'cattype':'Investment'},
        {'id':13, 'cattype':'Bills'},
        {'id':14, 'cattype':'Salary'},
        ]
    )

    subcategorytype_table = op.create_table('subcategorytype',
    sa.Column('id', sa.Integer(), nullable=True),
    sa.Column('subcattype', sa.String(length=128), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    op.bulk_insert(subcategorytype_table,
    [
        {'id':1, 'subcattype':'Rent'},
        {'id':2, 'subcattype':'EMI'},
        {'id':3, 'subcattype':'Electricity'},
        {'id':4, 'subcattype':'Utility'},
        {'id':5, 'subcattype':'Groceries'},
        {'id':6, 'subcattype':'Toiletries'},
        {'id':7, 'subcattype':'Accessories'},
        {'id':8, 'subcattype':'Dining out'},
        {'id':9, 'subcattype':'Furniture'},
        {'id':10, 'subcattype':'Equipments'},
        {'id':11, 'subcattype':'Seasonal'},
        {'id':12, 'subcattype':'Regular'},
        {'id':13, 'subcattype':'Formal'},
        {'id':14, 'subcattype':'Fashion'},
        {'id':15, 'subcattype':'Footwear'},
        {'id':16, 'subcattype':'Entertainment'},
        {'id':17, 'subcattype':'Hobbies'},
        {'id':18, 'subcattype':'Gifts'},
        {'id':19, 'subcattype':'Books'},
        {'id':20, 'subcattype':'Toys'},
        {'id':21, 'subcattype':'Membership'},
        {'id':22, 'subcattype':'Tickets'},
        {'id':23, 'subcattype':'Parking'},
        {'id':24, 'subcattype':'Insurance'},
        {'id':25, 'subcattype':'Maintenance'},
        {'id':26, 'subcattype':'Repair'},
        {'id':27, 'subcattype':'Medicines'},
        {'id':28, 'subcattype':'Hotel'},
        {'id':29, 'subcattype':'Food'},
        {'id':30, 'subcattype':'Shoopping'},
        {'id':31, 'subcattype':'Activities'},
        {'id':32, 'subcattype':'Reimbursement'},
        {'id':33, 'subcattype':'Donation'},
        {'id':34, 'subcattype':'Deduction'},
        {'id':35, 'subcattype':'Internet'},
        {'id':36, 'subcattype':'Telephone'},
        {'id':37, 'subcattype':'Equities'},
        {'id':38, 'subcattype':'Funds'},
        {'id':39, 'subcattype':'Deposits'},
        ]
    )


    transactiontype_table = op.create_table('transactiontype',
    sa.Column('id', sa.Integer(), nullable=True),
    sa.Column('ttype', sa.String(length=128), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    op.bulk_insert(transactiontype_table,
    [
        {'id':1, 'ttype':'credit card'},
        {'id':2, 'ttype':'check'},
        {'id':3, 'ttype':'cash'},
        {'id':4, 'ttype':'transfer'},
        {'id':5, 'ttype':'internal transfer'},
        {'id':6, 'ttype':'debit card'},
        {'id':7, 'ttype':'standing order'},
        {'id':8, 'ttype':'electronic payment'},
        {'id':9, 'ttype':'deposit'},
        ]
    )

    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=True),
    sa.Column('email', sa.String(length=64), nullable=True),
    sa.Column('password_hash', sa.String(length=128), nullable=True),
    sa.Column('last_seen', sa.DateTime(), nullable=True),
    sa.Column('is_admin', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username')
    )
    op.create_table('account',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.Column('number', sa.Integer(), nullable=True),
    sa.Column('holder', sa.String(length=64), nullable=True),
    sa.Column('currency', sa.String(length=64), nullable=True),
    sa.Column('balance', sa.Float(), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['holder'], ['user.username'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('scheduled_transaction',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=True),
    sa.Column('frequency', sa.String(length=128), nullable=True),
    sa.Column('interval', sa.Integer(), nullable=True),
    sa.Column('day', sa.Integer(), nullable=True),
    sa.Column('start', sa.DateTime(), nullable=True),
    sa.Column('end', sa.DateTime(), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=True),
    sa.Column('last_approved', sa.DateTime(), nullable=True),
    sa.Column('amount', sa.Float(), nullable=True),
    sa.Column('description', sa.String(length=128), nullable=True),
    sa.Column('type_id', sa.Integer(), nullable=True),
    sa.Column('category', sa.String(length=128), nullable=True),
    sa.Column('tag', sa.String(length=64), nullable=True),
    sa.Column('payee', sa.String(length=128), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['account.id'], ),
    sa.ForeignKeyConstraint(['type_id'], ['transactiontype.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('transaction',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=True),
    sa.Column('date', sa.DateTime(), nullable=False),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('type', sa.Integer(), nullable=True),
    sa.Column('description', sa.String(length=128), nullable=True),
    sa.Column('category', sa.String(length=128), nullable=True),
    sa.Column('subcategory', sa.String(length=128), nullable=True),
    sa.Column('tag', sa.String(length=64), nullable=True),
    sa.Column('status', sa.Boolean(), nullable=True),
    sa.Column('payee', sa.String(length=128), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['account.id'], ),
    sa.ForeignKeyConstraint(['type_id'], ['transactiontype.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('date', 'amount', 'type_id', 'description', 'category', name='unique_transactions')
    )
    op.create_index(op.f('ix_transaction_date'), 'transaction', ['date'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_transaction_date'), table_name='transaction')
    op.drop_table('transaction')
    op.drop_table('scheduled_transaction')
    op.drop_table('account')
    op.drop_table('user')
    op.drop_table('transactiontype')
    op.drop_table('subcategorytype')
    op.drop_table('categorytype')
    # ### end Alembic commands ###
