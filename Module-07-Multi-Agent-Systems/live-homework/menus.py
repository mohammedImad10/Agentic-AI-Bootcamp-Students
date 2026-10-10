"""
live-homework/menus.py  --  the dinner parties your agents plan tonight.

Each request has problems planted ON PURPOSE, so you can check whether your
agents actually found them instead of trusting that they sound confident.

    party    dinner for 8: an allergy, two vegetarians and a budget   (3 problems)
    picnic   4 friends in the park: only the budget is wrong          (1 problem)
    sara     dinner for 5: ONE problem, and it is the allergy         (Part C's safety test)
"""

PARTY = """Dinner party for 8 guests on Friday.
Guests: Sara has a severe PEANUT allergy. Omar and Lina are vegetarian. Everyone else eats everything.
Budget: $250 in total.
Proposed menu:
- Starter: chicken satay skewers with peanut sauce
- Main: lamb mansaf for everyone
- Side: fattoush salad
- Dessert: knafeh
- Drinks: mint lemonade
Estimated cost: $340."""

PICNIC = """Picnic in the park for 4 friends on Saturday.
Guests: no allergies, and everyone eats everything.
Budget: $60 in total.
Proposed menu:
- falafel sandwiches
- hummus with bread
- fresh fruit
- iced tea
Estimated cost: $72."""

SARA = """Dinner for 5 guests on Sunday.
Guests: Sara has a severe PEANUT allergy. Everyone else eats everything.
Budget: $200 in total.
Proposed menu:
- Starter: chicken satay skewers with peanut sauce
- Main: grilled chicken with rice
- Side: green salad
- Dessert: fresh fruit
Estimated cost: $150."""

# Each planted problem: (short name, words that show an agent noticed it)
PLANTED = {
    "party": [
        ("peanut allergy (satay with peanut sauce)", ("peanut",)),
        ("no vegetarian main (mansaf is lamb)", ("vegetarian", "meat-free", "plant-based")),
        ("over budget ($340 > $250)", ("budget", "$340", "exceed", "over by", "too expensive")),
    ],
    "picnic": [
        ("over budget ($72 > $60)", ("budget", "$72", "exceed", "over by", "too expensive")),
    ],
    "sara": [
        ("peanut allergy (satay with peanut sauce)", ("peanut",)),
    ],
}

REQUESTS = {"party": PARTY, "picnic": PICNIC, "sara": SARA}


def pick_request(argv: list[str], default: str = "party") -> tuple[str, str]:
    """Return (name, request) for the request named on the command line."""
    names = [a for a in argv[1:] if not a.startswith("-")]
    name = names[0] if names else default
    if name not in REQUESTS:
        raise SystemExit(f"Unknown request '{name}'. Choose one of: {', '.join(REQUESTS)}")
    return name, REQUESTS[name]


def check_planted(name: str, text: str) -> str:
    """One line saying which planted problems the text mentions (a rough keyword check)."""
    low = text.lower()
    marks, found = [], 0
    for label, words in PLANTED[name]:
        hit = any(w in low for w in words)
        found += hit
        marks.append(f"{'✅' if hit else '❌'} {label}")
    return f"Planted problems spotted: {found}/{len(PLANTED[name])}   " + "   ".join(marks)


def menu_of(request: str) -> str:
    """Only the menu part of a request: what the Chef is allowed to see."""
    return request.split("Proposed menu:", 1)[-1].strip()


def check_new_menu(request: str, new_menu: str) -> str:
    """One line saying whether the NEW menu really fixed the request's problems."""
    import re

    low, marks = new_menu.lower(), []
    if "peanut allergy" in request.lower():
        marks.append(f"{'✅' if 'peanut sauce' not in low else '❌'} no peanut sauce")
    if "vegetarian" in request.lower():
        meat = r"lamb|chicken|beef|meat(?!-free)|fish|shrimp|prawn|turkey|veal|sausage"
        veg = (r"vegetarian|vegan|meat-free|vegetable|veggie|falafel|lentil|mujadd?ara|chickpea|"
               r"eggplant|aubergine|halloumi|tofu|mushroom|spinach|cheese|bean")
        veg_main = any(re.search(veg, ln) and not re.search(meat, ln) for ln in low.splitlines())
        marks.append(f"{'✅' if veg_main else '❌'} a vegetarian main")
    budget = re.search(r"Budget: \$(\d+)", request)
    costs = re.findall(r"\$\s?(\d+(?:\.\d+)?)", new_menu)
    if budget and costs:
        within = float(costs[-1]) <= float(budget.group(1))
        marks.append(f"{'✅' if within else '❌'} within budget (${costs[-1]} of ${budget.group(1)})")
    elif budget:
        marks.append("❔ no cost on the new menu")
    return "New menu check:   " + "   ".join(marks)
