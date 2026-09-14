from app.crypto import aes_encrypt, aes_decrypt


def test_encrypt_decrypt_roundtrip():
    plain = "hello world"
    cipher = aes_encrypt(plain)
    assert cipher != plain
    assert aes_decrypt(cipher) == plain


def test_encrypt_different_inputs_different_outputs():
    assert aes_encrypt("a") != aes_encrypt("b")


def test_encrypt_chinese():
    plain = "你好，世界"
    assert aes_decrypt(aes_encrypt(plain)) == plain