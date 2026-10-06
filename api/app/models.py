from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class Ingredient(Base):
    __tablename__ = "ingredients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    aliases: Mapped[str] = mapped_column(Text, default="")
    function: Mapped[str] = mapped_column(String(160))
    irritant_level: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (CheckConstraint("irritant_level between 0 and 5", name="ck_ingredient_irritant"),)

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    brand: Mapped[str | None] = mapped_column(String(160), nullable=True)
    ingredients_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ingredients: Mapped[list["ProductIngredient"]] = relationship(back_populates="product", cascade="all, delete-orphan")

class ProductIngredient(Base):
    __tablename__ = "product_ingredients"
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)
    product: Mapped[Product] = relationship(back_populates="ingredients")
    ingredient: Mapped[Ingredient] = relationship()
    __table_args__ = (UniqueConstraint("product_id", "position", name="uq_product_position"),)

class Routine(Base):
    __tablename__ = "routines"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    skin_type: Mapped[str] = mapped_column(String(40), default="normal")
    items: Mapped[list["RoutineItem"]] = relationship(back_populates="routine", cascade="all, delete-orphan")

class RoutineItem(Base):
    __tablename__ = "routine_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    routine_id: Mapped[int] = mapped_column(ForeignKey("routines.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    slot: Mapped[str] = mapped_column(String(20), default="evening")
    routine: Mapped[Routine] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()
    __table_args__ = (CheckConstraint("slot in ('morning','evening')", name="ck_routine_slot"), UniqueConstraint("routine_id", "product_id", name="uq_routine_product"))

class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    ingredient_text: Mapped[str] = mapped_column(Text)
    skin_type: Mapped[str] = mapped_column(String(40), default="normal")
    ai_status: Mapped[str] = mapped_column(String(20), default="fake")
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
