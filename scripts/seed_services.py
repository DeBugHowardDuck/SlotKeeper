from slotkeeper.db.session import session_scope
from slotkeeper.db.models import Service

SERVICES = [
    ("Просмотр фильмов (экран + проектор)", False, 10),
    ("Sony PlayStation 5", False, 20),
    ("Караоке (Колонка + 3 микрофона)", False, 30),
    ("Настольные игры", False, 40),
    ("Попкорн", False, 50),
    ("Чай/Кофе", False, 60),
    ("Кальян, табак, уголь (18+)", True, 70),
]

if __name__ == "__main__":
    with session_scope() as s:
        exist = {r.name for r in s.query(Service).all()}
        for name, adult, order in SERVICES:
            if name in exist:
                continue
            s.add(Service(name=name, adult_only=adult, sort_order=order, is_active=True))
    print("Seed OK")
