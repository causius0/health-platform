"""
Authentication utilities for JWT token management and user login/logout.
"""
import bcrypt
from datetime import datetime, timedelta
from models import User
from flask_jwt_extended import create_access_token, get_jwt_identity

# JWT configuration
JWT_SECRET_KEY = "feem-salute-secret-key-2026"  # In production, use environment variable
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)


def verify_password(username, password):
    """Verify user credentials and return user if valid."""
    from models import Session
    session = Session()
    user = session.query(User).filter_by(username=username).first()

    if not user:
        session.close()
        return None

    # Verify password hash
    if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        session.close()
        return user

    session.close()
    return None


def login_user(username, password):
    """Authenticate user and return JWT token."""
    user = verify_password(username, password)

    if not user:
        return None, "Credenziali non valide"

    # Create JWT token with user ID as identity
    token = create_access_token(
        identity=str(user.id),  # Flask-JWT-Extended requires string identity
        expires_delta=JWT_ACCESS_TOKEN_EXPIRES
    )

    return token, "success", user


def get_current_user():
    """Get current authenticated user from JWT token."""
    from models import Session
    identity = get_jwt_identity()

    if not identity:
        return None

    session = Session()
    user = session.query(User).get(int(identity))  # identity is user_id as string
    session.close()

    return user


def cleanup_chat_on_logout(user_id):
    """Clear all chat data for user on logout (privacy requirement)."""
    from models import Session, ChatSession, ChatMessage
    session = Session()

    try:
        # Get all chat sessions for this user
        chat_sessions = session.query(ChatSession).filter_by(user_id=user_id).all()

        for chat_session in chat_sessions:
            # Delete all messages in this session
            session.query(ChatMessage).filter_by(session_id=chat_session.id).delete()

        # Delete all chat sessions for this user
        session.query(ChatSession).filter_by(user_id=user_id).delete()

        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Error cleaning up chat data: {e}")
        return False
    finally:
        session.close()
