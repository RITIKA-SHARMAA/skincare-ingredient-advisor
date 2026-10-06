from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision="0001_initial"
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table("ingredients", sa.Column("id",sa.Integer(),primary_key=True),sa.Column("name",sa.String(160),nullable=False,unique=True),sa.Column("aliases",sa.Text(),nullable=False,server_default=""),sa.Column("function",sa.String(160),nullable=False),sa.Column("irritant_level",sa.Integer(),nullable=False,server_default="0"),sa.CheckConstraint("irritant_level between 0 and 5",name="ck_ingredient_irritant"))
    op.create_index("ix_ingredients_name_trgm","ingredients",["name"],postgresql_using="gin",postgresql_ops={"name":"gin_trgm_ops"})
    op.create_table("products",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("name",sa.String(200),nullable=False),sa.Column("brand",sa.String(160)),sa.Column("ingredients_text",sa.Text(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("product_ingredients",sa.Column("product_id",sa.Integer(),sa.ForeignKey("products.id",ondelete="CASCADE"),primary_key=True),sa.Column("ingredient_id",sa.Integer(),sa.ForeignKey("ingredients.id"),primary_key=True),sa.Column("position",sa.Integer(),nullable=False),sa.UniqueConstraint("product_id","position",name="uq_product_position"))
    op.create_index("ix_product_ingredients_product","product_ingredients",["product_id"])
    op.create_table("routines",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("name",sa.String(200),nullable=False),sa.Column("skin_type",sa.String(40),nullable=False,server_default="normal"))
    op.create_table("routine_items",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("routine_id",sa.Integer(),sa.ForeignKey("routines.id",ondelete="CASCADE"),nullable=False),sa.Column("product_id",sa.Integer(),sa.ForeignKey("products.id",ondelete="CASCADE"),nullable=False),sa.Column("slot",sa.String(20),nullable=False,server_default="evening"),sa.CheckConstraint("slot in ('morning','evening')",name="ck_routine_slot"),sa.UniqueConstraint("routine_id","product_id",name="uq_routine_product"))
    op.create_index("ix_routine_items_routine_id","routine_items",["routine_id"])
    op.create_index("ix_routine_items_product_id","routine_items",["product_id"])
    op.create_table("analyses",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("ingredient_text",sa.Text(),nullable=False),sa.Column("skin_type",sa.String(40),nullable=False,server_default="normal"),sa.Column("ai_status",sa.String(20),nullable=False,server_default="fake"),sa.Column("result_json",sa.Text(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table("analyses"); op.drop_table("routine_items"); op.drop_table("routines"); op.drop_table("product_ingredients"); op.drop_table("products"); op.drop_index("ix_ingredients_name_trgm",table_name="ingredients"); op.drop_table("ingredients")
