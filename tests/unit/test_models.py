"""Unit tests for database models."""
import pytest
from app.models import User, Plant
from datetime import datetime

def test_new_user():
    """Test creating a new user."""
    user = User(username='test_user')
    user.set_password('test_password')
    assert user.username == 'test_user'
    assert user.check_password('test_password')
    assert not user.check_password('wrong_password')
    assert not user.is_admin

def test_new_admin_user():
    """Test creating a new admin user."""
    admin = User(username='admin', is_admin=True)
    admin.set_password('admin_password')
    assert admin.username == 'admin'
    assert admin.is_admin
    assert admin.check_password('admin_password')

def test_new_plant():
    """Test creating a new plant."""
    user = User(username='plant_owner')
    plant = Plant(
        name='Test Plant',
        strain='Test Strain',
        owner=user,
        start_date=datetime.utcnow(),
        is_group_grow=False,
        is_public=True
    )
    assert plant.name == 'Test Plant'
    assert plant.strain == 'Test Strain'
    assert plant.owner == user
    assert not plant.is_group_grow
    assert plant.is_public
