"""Functional tests for authentication."""
import pytest
from flask import g, session

def test_login(client, auth):
    """Test login functionality."""
    # Test GET request
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert b'Login' in response.data

    # Test successful login
    response = auth.login()
    assert response.headers['Location'] == '/'

    # Test login with client session
    with client:
        client.get('/')
        assert session['_user_id'] is not None
        assert g.user.username == 'test_user'

def test_logout(client, auth):
    """Test logout functionality."""
    auth.login()

    with client:
        auth.logout()
        assert '_user_id' not in session

def test_login_required(client):
    """Test that certain pages require login."""
    response = client.get('/')
    assert response.headers['Location'] == '/auth/login'

def test_admin_required(client, auth):
    """Test that admin pages require admin privileges."""
    auth.login()  # Login as regular user
    response = client.get('/auth/manage_users')
    assert response.status_code == 302  # Redirect

    # Login as admin
    auth.login(username='admin', password='admin_password')
    response = client.get('/auth/manage_users')
    assert response.status_code == 200
