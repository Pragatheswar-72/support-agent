import os
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "support_agent.db"


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(100))
    item: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20))  # placed/shipped/delivered/cancelled
    order_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Float)


class Payment(Base):
    __tablename__ = "payments"

    payment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id"))
    status: Mapped[str] = mapped_column(String(20))  # pending/paid/refunded
    method: Mapped[str] = mapped_column(String(30))
    amount: Mapped[float] = mapped_column(Float)


class Refund(Base):
    __tablename__ = "refunds"

    refund_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id"))
    status: Mapped[str] = mapped_column(String(20), default="none")  # none/requested/approved/completed
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)


def get_engine(db_url: str | None = None):
    default_url = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
    url = db_url or os.environ.get("SUPPORT_AGENT_DB_URL", default_url)
    return create_engine(url, echo=False)


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


def get_session_factory(engine):
    return sessionmaker(bind=engine)
