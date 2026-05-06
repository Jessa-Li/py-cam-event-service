import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db as _db
from app.models import User


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_header(app):
    with app.app_context():
        token = create_access_token(identity="test-camera")
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_token(app):
    """A real admin token — needed by tests that hit admin-gated routes
    like POST /cameras."""
    with app.app_context():
        user = User(email="seed-admin@example.com", is_admin=True)
        user.set_password("seed")
        _db.session.add(user)
        _db.session.commit()
        return create_access_token(
            identity=str(user.id),
            additional_claims={"is_admin": True, "email": user.email},
        )