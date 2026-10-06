from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Ingredient, Product, ProductIngredient, Routine, RoutineItem

# Conflict data is stored as ingredient function pairs so rules remain data-driven.
CONFLICT_FUNCTIONS = {
    frozenset({"chemical exfoliant", "retinoid"}): "Strong exfoliation and retinoid use may be too irritating together.",
    frozenset({"chemical exfoliant", "chemical exfoliant"}): "Two strong exfoliating products may increase irritation when layered.",
}

def routine_conflicts(db: Session, routine: Routine):
    products=db.scalars(select(Product).join(RoutineItem, RoutineItem.product_id==Product.id).where(RoutineItem.routine_id==routine.id)).unique().all()
    rows=[]
    for i,a in enumerate(products):
        af={x.ingredient.function.lower() for x in a.ingredients}
        for b in products[i+1:]:
            bf={x.ingredient.function.lower() for x in b.ingredients}
            reason=None
            for key,msg in CONFLICT_FUNCTIONS.items():
                if key.issubset(af|bf) and any(k in af for k in key) and any(k in bf for k in key): reason=msg; break
            if reason: rows.append({"product_a":a.name,"product_b":b.name,"reason":reason})
    return rows
