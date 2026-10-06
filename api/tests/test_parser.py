from app.parser import split_ingredients

def test_split_normalises():
    assert split_ingredients(" Water,  Glycerin;Niacinamide\n") == ["water","glycerin","niacinamide"]
