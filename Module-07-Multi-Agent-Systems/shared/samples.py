"""
shared/samples.py  --  the code our agents review today.

Each sample has problems planted ON PURPOSE, so you can check whether your
agents actually found them instead of just trusting that they sound confident.

    orders      touches a database  ->  a security problem is in there
    split_bill  pure arithmetic     ->  nothing for a security reviewer to do
    find_user   ONE problem only, and it is a security problem (the trust demo)
"""

ORDERS = '''import sqlite3

def average_order_value(customer_name):
    conn = sqlite3.connect("shop.db")
    query = "SELECT amount FROM orders WHERE customer = '" + customer_name + "'"
    rows = conn.execute(query).fetchall()
    total = 0
    for row in rows:
        total = total + row[0]
    return total / len(rows)
'''

SPLIT_BILL = '''def split_bill(total, people):
    share = round(total / people, 2)
    return [share] * people
'''

# Only ONE problem, and it is a security problem. Used in the trust demo.
FIND_USER = '''def find_user(conn, username):
    query = "SELECT id, email FROM users WHERE name = '" + username + "'"
    return conn.execute(query).fetchone()
'''

# Each planted problem: (short name, words that show a reviewer noticed it)
PLANTED = {
    "orders": [
        ("SQL injection", ("inject", "parameteriz", "parametris", "sanitiz")),
        ("crash when the customer has no orders", ("zero", "empty", "no orders", "no rows")),
        ("connection never closed", ("close", "leak", "context manager")),
    ],
    "split_bill": [
        ("crash when people is 0", ("zero", "people == 0", "people is 0", "no people")),
        ("shares may not add up to the total", ("add up", "sum", "remainder", "cent", "99.99", "rounding")),
    ],
    "find_user": [
        ("SQL injection", ("inject", "parameteriz", "parametris", "sanitiz")),
    ],
}

SAMPLES = {"orders": ORDERS, "split_bill": SPLIT_BILL, "find_user": FIND_USER}


def pick_sample(argv: list[str]) -> tuple[str, str]:
    """Return (name, code) for the sample named on the command line, default 'orders'."""
    names = [a for a in argv[1:] if not a.startswith("-")]
    name = names[0] if names else "orders"
    if name not in SAMPLES:
        raise SystemExit(f"Unknown sample '{name}'. Choose one of: {', '.join(SAMPLES)}")
    return name, SAMPLES[name]


def check_planted(sample_name: str, text: str) -> str:
    """One line saying which planted problems the text mentions (a rough keyword check)."""
    low = text.lower()
    marks = []
    found = 0
    for label, words in PLANTED[sample_name]:
        hit = any(w in low for w in words)
        found += hit
        marks.append(f"{'✅' if hit else '❌'} {label}")
    return f"Planted problems spotted: {found}/{len(PLANTED[sample_name])}   " + "   ".join(marks)
