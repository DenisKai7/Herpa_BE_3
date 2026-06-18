import secrets, uuid


def uuid_str() -> str:
    return str(uuid.uuid4())


def share_token() -> str:
    return secrets.token_urlsafe(32)
