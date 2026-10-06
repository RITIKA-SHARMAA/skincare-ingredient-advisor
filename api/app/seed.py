"""Load the illustrative ingredient catalogue and conflict rules. Safe to re-run."""

import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import ConflictRule, Ingredient

DATA = Path(__file__).resolve().parent.parent / "data"


def seed(db: Session) -> tuple[int, int]:
    added_ingredients = added_rules = 0
    existing = set(db.scalars(select(Ingredient.name)))
    with (DATA / "ingredients.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["name"] in existing:
                continue
            db.add(
                Ingredient(
                    name=row["name"],
                    aliases=row["aliases"],
                    function=row["function"],
                    irritant_level=int(row["irritant_level"]),
                )
            )
            added_ingredients += 1
    pairs = {(r.function_a, r.function_b) for r in db.scalars(select(ConflictRule))}
    with (DATA / "conflict_rules.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row["function_a"], row["function_b"]) in pairs:
                continue
            db.add(ConflictRule(**row))
            added_rules += 1
    db.commit()
    return added_ingredients, added_rules


def main() -> None:
    with SessionLocal() as db:
        ingredients, rules = seed(db)
    print(f"seeded {ingredients} ingredients and {rules} conflict rules")


if __name__ == "__main__":
    main()
