from cryptography.fernet import Fernet
from .config import settings

# 确保密钥是字节串
key = settings.ENCRYPTION_KEY.encode()
cipher_suite = Fernet(key)

def encrypt_password(password: str) -> str:
    """加密密码"""
    encrypted_text = cipher_suite.encrypt(password.encode())
    return encrypted_text.decode()

def decrypt_password(encrypted_password: str) -> str:
    """解密密码"""
    decrypted_text = cipher_suite.decrypt(encrypted_password.encode())
    return decrypted_text.decode()