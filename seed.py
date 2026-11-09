
import hashlib
import secrets

from database import SessionLocal, engine, Base
from models import Product, Retailer, User


# Create database tables
Base.metadata.create_all(bind=engine)


def hash_password(password):
    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        310000
    ).hex()

    return f"pbkdf2_sha256$310000${salt}${password_hash}"


db = SessionLocal()

products = [
    Product(
        sku_code="SKU-BS-075",
        name="Glucose Biscuit 75g",
        dealer_price=8.10,
        stock_cases=340,
        scheme_type="buy_x_get_y",
        scheme_value=10
    ),
    Product(
        sku_code="SKU-DT-1KG",
        name="Detergent Powder 1kg",
        dealer_price=101.50,
        stock_cases=85,
        scheme_type="discount",
        scheme_value=3
    ),
    Product(
        sku_code="SKU-TE-250",
        name="Tea Leaf 250g",
        dealer_price=118.00,
        stock_cases=0,
        scheme_type="none",
        scheme_value=0
    )
]

try:
    # Insert sample products without resetting existing stock
    for product in products:
        existing = db.query(Product).filter_by(
            sku_code=product.sku_code
        ).first()

        if not existing:
            db.add(product)

    # Insert sample retailer if it does not exist
    retailer = db.query(Retailer).filter_by(
        phone="9876543210"
    ).first()

    if not retailer:
        retailer = Retailer(
            name="Shree Kirana Store",
            phone="9876543210",
            credit_limit=50000
        )
        db.add(retailer)
        db.flush()

    # Create retailer demo account
    retailer_user = db.query(User).filter_by(
        username="retailer_demo"
    ).first()

    if not retailer_user:
        db.add(
            User(
                username="retailer_demo",
                password_hash=hash_password("Retailer@123"),
                role="retailer",
                retailer_id=retailer.id
            )
        )

    # Create staff demo account
    staff_user = db.query(User).filter_by(
        username="staff_demo"
    ).first()

    if not staff_user:
        db.add(
            User(
                username="staff_demo",
                password_hash=hash_password("Staff@123"),
                role="staff",
                retailer_id=None
            )
        )

    db.commit()

    print("Sample products, retailer and demo users are ready!")

except Exception as e:
    db.rollback()
    print("Error:", e)

finally:
    db.close()
