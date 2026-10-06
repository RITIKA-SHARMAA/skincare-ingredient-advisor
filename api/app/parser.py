import re
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session
from .models import Ingredient

ALIASES = {"vitamin c": "ascorbic acid", "bha": "salicylic acid", "aha": "alpha hydroxy acids", "vitamin b3": "niacinamide", "tocopherol": "vitamin e"}

def split_ingredients(raw: str) -> list[str]:
    parts = re.split(r"[,;\n]+", raw)
    return [re.sub(r"\s+", " ", p.strip(" .:-").lower()) for p in parts if p.strip(" .:-")]

def resolve_ingredients(db: Session, raw: str):
    names = split_ingredients(raw)
    catalogue = {x.name.lower(): x for x in db.scalars(select(Ingredient)).all()}
    for ingredient in catalogue.values():
        for alias in filter(None, (a.strip().lower() for a in ingredient.aliases.split(","))):
            catalogue.setdefault(alias, ingredient)
    resolved, unmatched = [], []
    for pos, name in enumerate(names):
        canonical = ALIASES.get(name, name)
        match = catalogue.get(canonical)
        if not match:
            match = db.scalar(select(Ingredient).where(func.lower(Ingredient.name) == canonical))
        if match: resolved.append((pos, match))
        else: unmatched.append({"position": pos, "name": name})
    return resolved, unmatched
