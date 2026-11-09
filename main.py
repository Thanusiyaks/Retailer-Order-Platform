
import os
import csv
import json
import hmac
import hashlib
import secrets
import base64
from io import StringIO
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import engine, Base, get_db
import models


app = FastAPI(
    title="FMCG OrderHub API",
    description="Backend API for FMCG retailer ordering",
    version="2.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
         "http://localhost:5173",
         "http://127.0.0.1:5173",
         "http://localhost:5174",
         "http://127.0.0.1:5174"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


Base.metadata.create_all(bind=engine)


# Set JWT_SECRET_KEY in the environment before deployment.
# This fallback is only for local development.
SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "development-only-change-this-secret"
)

TOKEN_EXPIRE_HOURS = 8

security = HTTPBearer(auto_error=False)

class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class OrderItemRequest(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=10000)


class OrderCreateRequest(BaseModel):
    retailer_id: int
    items: list[OrderItemRequest] = Field(min_length=1, max_length=100)


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt, expected_hash = stored_hash.split("$")

        if algorithm != "pbkdf2_sha256":
            return False

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            int(iterations)
        ).hex()

        return hmac.compare_digest(actual_hash, expected_hash)

    except (ValueError, TypeError):
        return False


def create_access_token(username):
    payload = {
        "sub": username,
        "exp": int(
            (datetime.now(timezone.utc) +
             timedelta(hours=TOKEN_EXPIRE_HOURS)).timestamp()
        )
    }

    payload_bytes = json.dumps(payload).encode("utf-8")

    encoded_payload = base64.urlsafe_b64encode(
        payload_bytes
    ).decode("utf-8").rstrip("=")

    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256
    ).digest()

    encoded_signature = base64.urlsafe_b64encode(
        signature
    ).decode("utf-8").rstrip("=")

    return f"{encoded_payload}.{encoded_signature}"


def decode_access_token(token):
    try:
        encoded_payload, encoded_signature = token.split(".")

        expected_signature = hmac.new(
            SECRET_KEY.encode("utf-8"),
            encoded_payload.encode("utf-8"),
            hashlib.sha256
        ).digest()

        actual_signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )

        if not hmac.compare_digest(
            expected_signature,
            actual_signature
        ):
            raise ValueError("Invalid signature")

        payload_bytes = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )

        payload = json.loads(payload_bytes.decode("utf-8"))

        if payload.get("exp", 0) < int(
            datetime.now(timezone.utc).timestamp()
        ):
            raise ValueError("Token expired")

        username = payload.get("sub")

        if not username:
            raise ValueError("Username missing")

        return username

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired login session",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Please sign in to continue",
            headers={"WWW-Authenticate": "Bearer"}
        )

    username = decode_access_token(credentials.credentials)

    user = db.query(models.User).filter(
        models.User.username == username
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User account not found"
        )

    return user


def require_staff(
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "staff":
        raise HTTPException(
            status_code=403,
            detail="Staff access required"
        )

    return current_user


@app.get("/")
def home():
    return {
        "message": "Welcome to FMCG OrderHub API",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/auth/login")
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(
        models.User.username == login_data.username
    ).first()

    if not user or not verify_password(
        login_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )

    access_token = create_access_token(user.username)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": TOKEN_EXPIRE_HOURS * 60 * 60
    }


@app.get("/me")
def get_me(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    retailer = None

    if current_user.retailer_id:
        retailer = db.query(models.Retailer).filter(
            models.Retailer.id == current_user.retailer_id
        ).first()

    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "retailer": (
            {
                "id": retailer.id,
                "name": retailer.name,
                "phone": retailer.phone,
                "credit_limit": retailer.credit_limit
            }
            if retailer else None
        )
    }


@app.get("/products")
def get_products(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    products = db.query(models.Product).all()

    return [
        {
            "id": p.id,
            "sku_code": p.sku_code,
            "name": p.name,
            "dealer_price": p.dealer_price,
            "stock_cases": p.stock_cases,
            "scheme_type": p.scheme_type,
            "scheme_value": p.scheme_value
        }
        for p in products
    ]


@app.get("/retailers")
def get_retailers(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "retailer":
        retailers = db.query(models.Retailer).filter(
            models.Retailer.id == current_user.retailer_id
        ).all()
    else:
        retailers = db.query(models.Retailer).all()

    return [
        {
            "id": r.id,
            "name": r.name,
            "phone": r.phone,
            "credit_limit": r.credit_limit
        }
        for r in retailers
    ]


@app.post("/orders")
def create_order(
    order_data: OrderCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Retailers can only place orders for their own store.
    if current_user.role == "retailer":
        if not current_user.retailer_id:
            raise HTTPException(
                status_code=403,
                detail="Your account is not linked to a retailer"
            )

        retailer_id = current_user.retailer_id

    else:
        retailer_id = order_data.retailer_id

    retailer = db.query(models.Retailer).filter(
        models.Retailer.id == retailer_id
    ).first()

    if not retailer:
        raise HTTPException(
            status_code=404,
            detail="Retailer not found"
        )

    if not order_data.items:
        raise HTTPException(
            status_code=400,
            detail="Order must contain at least one product"
        )

    product_ids = [item.product_id for item in order_data.items]

    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=400,
            detail="Do not add the same product more than once"
        )

    order_items = []
    total_amount = Decimal("0")

    for item in order_data.items:
        product = db.query(models.Product).filter(
            models.Product.id == item.product_id
        ).first()

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product ID {item.product_id} not found"
            )

        free_quantity = 0
        discount = Decimal("0")

        if product.scheme_type == "buy_x_get_y":
            scheme_value = int(product.scheme_value)

            if scheme_value <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid scheme configuration for {product.name}"
                )

            free_quantity = item.quantity // scheme_value

        elif product.scheme_type == "discount" and item.quantity >= 5:
            discount = (
                Decimal(str(product.scheme_value)) / Decimal("100")
            )

        required_stock = item.quantity + free_quantity

        if product.stock_cases < required_stock:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.name}"
            )

        subtotal = (
            Decimal(item.quantity)
            * Decimal(str(product.dealer_price))
            * (Decimal("1") - discount)
        )

        subtotal = subtotal.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        total_amount += subtotal

        order_items.append({
            "product": product,
            "quantity": item.quantity,
            "free_quantity": free_quantity,
            "unit_price": product.dealer_price,
            "subtotal": subtotal
        })

    try:
        new_order = models.Order(
            retailer_id=retailer.id,
            total_amount=float(total_amount),
            status="Pending"
        )

        db.add(new_order)
        db.flush()

        for item in order_items:
            product = item["product"]

            product.stock_cases -= (
                item["quantity"] + item["free_quantity"]
            )

            new_item = models.OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                free_quantity=item["free_quantity"],
                subtotal=float(item["subtotal"])
            )

            db.add(new_item)

        db.commit()
        db.refresh(new_order)

        return {
            "message": "Order placed successfully",
            "order_id": new_order.id,
            "retailer": retailer.name,
            "total_amount": new_order.total_amount,
            "status": new_order.status,
            "items": [
                {
                    "product": item["product"].name,
                    "quantity": item["quantity"],
                    "free_quantity": item["free_quantity"],
                    "subtotal": float(item["subtotal"])
                }
                for item in order_items
            ]
        }

    except Exception:
        db.rollback()
        raise


@app.get("/orders")
def get_orders(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Order)

    # Retailers can only view their own orders.
    if current_user.role == "retailer":
        query = query.filter(
            models.Order.retailer_id == current_user.retailer_id
        )

    orders = query.order_by(
        models.Order.id.desc()
    ).all()

    result = []

    for order in orders:
        items = db.query(models.OrderItem).filter(
            models.OrderItem.order_id == order.id
        ).all()

        result.append({
            "order_id": order.id,
            "retailer": (
                order.retailer.name if order.retailer else None
            ),
            "total_amount": order.total_amount,
            "status": order.status,
            "created_at": (
                order.created_at.isoformat()
                if order.created_at else None
            ),
            "items": [
                {
                    "product": (
                        item.product.name if item.product else None
                    ),
                    "quantity": item.quantity,
                    "free_quantity": item.free_quantity,
                    "unit_price": item.unit_price,
                    "subtotal": item.subtotal
                }
                for item in items
            ]
        })

    return result

@app.get("/orders/export/tally")
def export_tally_csv(
    current_user: models.User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    orders = db.query(models.Order).order_by(
        models.Order.id.asc()
    ).all()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Order ID",
        "Date",
        "Retailer Name",
        "Product Name",
        "Quantity",
        "Free Quantity",
        "Unit Price",
        "Subtotal",
        "Total Amount",
        "Status"
    ])

    for order in orders:
        items = db.query(models.OrderItem).filter(
            models.OrderItem.order_id == order.id
        ).all()

        for item in items:
            writer.writerow([
                order.id,
                (
                    order.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if order.created_at else ""
                ),
                order.retailer.name if order.retailer else "",
                item.product.name if item.product else "",
                item.quantity,
                item.free_quantity,
                item.unit_price,
                item.subtotal,
                order.total_amount,
                order.status
            ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=tally_orders.csv"
        }
    )
