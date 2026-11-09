
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku_code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    dealer_price = Column(Float, nullable=False)
    stock_cases = Column(Integer, default=0)
    scheme_type = Column(String, default="none")
    scheme_value = Column(Float, default=0)


class Retailer(Base):
    __tablename__ = "retailers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    credit_limit = Column(Float, default=0)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    retailer_id = Column(Integer, ForeignKey("retailers.id"), nullable=True)

    retailer = relationship("Retailer")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    retailer_id = Column(Integer, ForeignKey("retailers.id"))
    total_amount = Column(Float, nullable=False)
    status = Column(String, default="Pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    retailer = relationship("Retailer")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    free_quantity = Column(Integer, default=0)
    subtotal = Column(Float, nullable=False)

    order = relationship("Order")
    product = relationship("Product")
