import hashlib
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def generate_file_hash(file_bytes: bytes) -> str:
    """Generate SHA256 hash of a file or string"""
    h = hashlib.sha256()
    h.update(file_bytes)
    return h.hexdigest()
