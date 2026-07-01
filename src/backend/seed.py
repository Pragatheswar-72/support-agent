from datetime import date

from src.backend.db import Order, Payment, Refund, get_engine, get_session_factory, init_db

ORDERS = [
    # order_id, customer_name, item, status, order_date, amount
    (1001, "Alice Chen", "Wireless Headphones", "delivered", date(2026, 6, 1), 79.99),
    (1002, "Ben Torres", "Mechanical Keyboard", "shipped", date(2026, 6, 20), 129.00),
    (1003, "Carla Diaz", "USB-C Hub", "placed", date(2026, 6, 28), 34.50),
    (1004, "Dev Patel", "Standing Desk", "delivered", date(2026, 5, 15), 349.00),
    (1005, "Elena Novak", "Desk Lamp", "cancelled", date(2026, 6, 10), 24.99),
    (1006, "Farid Haidari", "Bluetooth Speaker", "delivered", date(2026, 6, 5), 59.99),
    (1007, "Grace Kim", "Laptop Stand", "shipped", date(2026, 6, 25), 42.00),
    (1008, "Hassan Ali", "Webcam 1080p", "placed", date(2026, 6, 29), 55.00),
    (1009, "Ines Moreau", "Ergonomic Mouse", "delivered", date(2026, 6, 12), 29.99),
    (1010, "Jonas Weber", "Noise-Cancelling Earbuds", "shipped", date(2026, 6, 27), 149.00),
]

PAYMENTS = [
    # payment_id, order_id, status, method, amount
    (1, 1001, "paid", "card", 79.99),
    (2, 1002, "paid", "card", 129.00),
    (3, 1003, "pending", "card", 34.50),
    (4, 1004, "paid", "paypal", 349.00),
    (5, 1005, "refunded", "card", 24.99),
    (6, 1006, "paid", "card", 59.99),
    (7, 1007, "paid", "paypal", 42.00),
    (8, 1008, "pending", "card", 55.00),
    (9, 1009, "paid", "card", 29.99),
    (10, 1010, "paid", "card", 149.00),
]

REFUNDS = [
    # refund_id, order_id, status, reason
    (1, 1001, "none", None),
    (2, 1002, "none", None),
    (3, 1003, "none", None),
    (4, 1004, "requested", "Item arrived damaged"),
    (5, 1005, "completed", "Order cancelled before shipping"),
    (6, 1006, "none", None),
    (7, 1007, "none", None),
    (8, 1008, "none", None),
    (9, 1009, "none", None),
    (10, 1010, "none", None),
]


def seed(session) -> None:
    for order_id, customer_name, item, status, order_date, amount in ORDERS:
        session.merge(
            Order(
                order_id=order_id,
                customer_name=customer_name,
                item=item,
                status=status,
                order_date=order_date,
                amount=amount,
            )
        )
    for payment_id, order_id, status, method, amount in PAYMENTS:
        session.merge(
            Payment(payment_id=payment_id, order_id=order_id, status=status, method=method, amount=amount)
        )
    for refund_id, order_id, status, reason in REFUNDS:
        session.merge(Refund(refund_id=refund_id, order_id=order_id, status=status, reason=reason))
    session.commit()


if __name__ == "__main__":
    engine = get_engine()
    init_db(engine)
    session = get_session_factory(engine)()
    seed(session)
    print(f"Seeded {len(ORDERS)} orders, {len(PAYMENTS)} payments, {len(REFUNDS)} refunds.")
