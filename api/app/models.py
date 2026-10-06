from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

SLOT_CHECK = "slot in ('morning','evening')"


class Ingredient(Base):
    __tablename__ = "ingredients"
    __table_args__ = (
        CheckConstraint("irritant_level between 0 and 5", name="ck_ingredient_irritant"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    # Pipe-separated alternative names, for example "aqua|eau".
    aliases: Mapped[str] = mapped_column(Text, default="")
    function: Mapped[str] = mapped_column(String(160))
    irritant_level: Mapped[int] = mapped_column(Integer, default=0)

    def alias_list(self) -> list[str]:
        return [alias.strip().lower() for alias in self.aliases.split("|") if alias.strip()]


class ConflictRule(Base):
    __tablename__ = "conflict_rules"
    __table_args__ = (
        UniqueConstraint("function_a", "function_b", name="uq_conflict_pair"),
        CheckConstraint("severity in ('low','medium','high')", name="ck_conflict_severity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    function_a: Mapped[str] = mapped_column(String(160))
    function_b: Mapped[str] = mapped_column(String(160))
    severity: Mapped[str] = mapped_column(String(10))
    reason: Mapped[str] = mapped_column(Text)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    brand: Mapped[str | None] = mapped_column(String(160), nullable=True)
    ingredients_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ingredients: Mapped[list["ProductIngredient"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductIngredient.position",
    )


class ProductIngredient(Base):
    __tablename__ = "product_ingredients"
    __table_args__ = (UniqueConstraint("product_id", "position", name="uq_product_position"),)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)
    product: Mapped[Product] = relationship(back_populates="ingredients")
    ingredient: Mapped[Ingredient] = relationship()


class Routine(Base):
    __tablename__ = "routines"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    skin_type: Mapped[str] = mapped_column(String(40), default="normal")
    items: Mapped[list["RoutineItem"]] = relationship(
        back_populates="routine", cascade="all, delete-orphan", order_by="RoutineItem.id"
    )


class RoutineItem(Base):
    __tablename__ = "routine_items"
    __table_args__ = (
        CheckConstraint(SLOT_CHECK, name="ck_routine_slot"),
        UniqueConstraint("routine_id", "product_id", name="uq_routine_product"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    routine_id: Mapped[int] = mapped_column(
        ForeignKey("routines.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    slot: Mapped[str] = mapped_column(String(20), default="evening")
    routine: Mapped[Routine] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    ingredient_text: Mapped[str] = mapped_column(Text)
    skin_type: Mapped[str] = mapped_column(String(40), default="normal")
    ai_status: Mapped[str] = mapped_column(String(20))
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
