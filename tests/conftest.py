import os
import tempfile

import pytest
from app import create_app
from app.extensions import db
from app.models import User

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create a temporary file to isolate the database for each test
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False
    })

    # Create the database and load test data
    with app.app_context():
        db.create_all()
        
        # Create test user
        user = User(username='test_user')
        user.set_password('test_password')
        db.session.add(user)
        
        # Create admin user
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin_password')
        db.session.add(admin)
        
        db.session.commit()

    yield app

    # Close and remove the temporary database
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def auth(client):
    """Authentication helper for tests."""
    class AuthActions:
        def login(self, username='test_user', password='test_password'):
            return client.post(
                '/auth/login',
                data={'username': username, 'password': password}
            )

        def logout(self):
            return client.get('/auth/logout')

    return AuthActions()
