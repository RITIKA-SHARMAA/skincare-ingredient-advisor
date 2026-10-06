import csv
from sqlalchemy import select
from .db import SessionLocal
from .models import Ingredient

def main():
    db=SessionLocal()
    with open("data/ingredients.csv",newline="",encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not db.scalar(select(Ingredient).where(Ingredient.name==row["name"])): db.add(Ingredient(name=row["name"],aliases=row["aliases"],function=row["function"],irritant_level=int(row["irritant_level"])))
    db.commit(); db.close()
if __name__=="__main__": main()
