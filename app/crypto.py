import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

from app.config import Config


def _get_key_iv():
    key = Config.AES_KEY.encode("utf-8")
    iv = Config.AES_IV.encode("utf-8")
    if len(key) != 32:
        raise ValueError("AES_KEY 必须是 32 字节（AES-256）")
    if len(iv) != 16:
        raise ValueError("AES_IV 必须是 16 字节")
    return key, iv


def aes_encrypt(plain_text: str) -> str:
    """AES-256-CBC 加密，返回 base64 字符串"""
    key, iv = _get_key_iv()
    data = plain_text.encode("utf-8")

    padder = padding.PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    cipher_bytes = encryptor.update(padded) + encryptor.finalize()

    return base64.b64encode(cipher_bytes).decode("utf-8")


def aes_decrypt(cipher_text: str) -> str:
    """AES-256-CBC 解密"""
    key, iv = _get_key_iv()
    cipher_bytes = base64.b64decode(cipher_text)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(cipher_bytes) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded) + unpadder.finalize()

    return data.decode("utf-8")