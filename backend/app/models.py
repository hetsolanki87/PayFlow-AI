from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base
class Client(Base):
    __tablename__='clients'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(254))
class Invoice(Base):
    __tablename__='invoices'
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey('clients.id'))
    description: Mapped[str] = mapped_column(Text)
    amount: Mapped[float] = mapped_column(Numeric(12,2))
    currency: Mapped[str] = mapped_column(String(3),default='USD')
    due_date: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(30),default='DRAFT')
    paypal_invoice_id: Mapped[str|None] = mapped_column(String(120),unique=True,nullable=True)
    paypal_url: Mapped[str|None] = mapped_column(Text,nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True),server_default=func.now())
    client: Mapped[Client] = relationship()
class WebhookEvent(Base):
    __tablename__='webhook_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(150),unique=True)
    event_type: Mapped[str] = mapped_column(String(150))
