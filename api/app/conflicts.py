"""Routine conflict detection driven by the conflict_rules table."""

from itertools import combinations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ConflictRule, Product, Routine
from .schemas import ConflictOut

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def product_functions(product: Product) -> set[str]:
    return {link.ingredient.function.lower() for link in product.ingredients}


def rule_applies(rule: ConflictRule, a: set[str], b: set[str]) -> bool:
    fa, fb = rule.function_a.lower(), rule.function_b.lower()
    return (fa in a and fb in b) or (fb in a and fa in b)


def find_conflicts(rules: list[ConflictRule], routine: Routine) -> list[ConflictOut]:
    """Compare every pair of products that share a slot; report the most severe rule per pair."""
    conflicts: list[ConflictOut] = []
    for slot in ("morning", "evening"):
        products = [item.product for item in routine.items if item.slot == slot]
        for first, second in combinations(products, 2):
            a, b = product_functions(first), product_functions(second)
            hits = [rule for rule in rules if rule_applies(rule, a, b)]
            if not hits:
                continue
            worst = min(hits, key=lambda rule: SEVERITY_ORDER[rule.severity])
            conflicts.append(
                ConflictOut(
                    slot=slot,
                    product_a=first.name,
                    product_b=second.name,
                    severity=worst.severity,
                    reason=worst.reason,
                )
            )
    return sorted(conflicts, key=lambda c: SEVERITY_ORDER[c.severity])


def routine_conflicts(db: Session, routine: Routine) -> list[ConflictOut]:
    rules = list(db.scalars(select(ConflictRule)))
    return find_conflicts(rules, routine)
