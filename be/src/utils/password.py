import bcrypt


def hash_password(password: str) -> str:
    """Hash a plaintext password with a freshly generated bcrypt salt.

    :param password: plaintext password
    :return: bcrypt hash (salt is embedded in the returned string)
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def validate_password(password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a previously hashed value.

    :param password: plaintext password to verify
    :param hashed_password: value produced by :func:`hash_password`
    :return: ``True`` if the password matches the hash
    """
    return bcrypt.checkpw(password.encode(), hashed_password.encode())
