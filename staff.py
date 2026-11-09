
import hashlib
import secrets
from getpass import getpass

from database import SessionLocal
import models


def hash_password(password):
    iterations = 310000
    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations
    ).hex()

    return f"pbkdf2_sha256${iterations}${salt.hex()}${password_hash}"


db = SessionLocal()

try:
    password = getpass("Enter your NEW staff password: ")
    confirm_password = getpass("Confirm your NEW staff password: ")

    if len(password) < 8:
        print("Password must contain at least 8 characters.")

    elif password != confirm_password:
        print("Passwords do not match.")

    else:
        staff = db.query(models.User).filter(
            models.User.username == "staff_demo"
        ).first()

        if staff:
            staff.password_hash = hash_password(password)
            staff.role = "staff"
            staff.retailer_id = None
            db.commit()

            print("Staff password reset successfully!")

        else:
            staff = models.User(
                username="staff_demo",
                password_hash=hash_password(password),
                role="staff",
                retailer_id=None
            )

            db.add(staff)
            db.commit()

            print("Staff account created successfully!")

        print("Username: staff_demo")

finally:
    db.close()
