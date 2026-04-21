from app.security.passwords import hash_password, verify_password


def test_hash_and_verify():
    h = hash_password("Secret123!")
    assert h != "Secret123!"
    assert verify_password("Secret123!", h) is True
    assert verify_password("wrong", h) is False


def test_hash_is_salted():
    a = hash_password("same")
    b = hash_password("same")
    assert a != b
