from flask import Flask
from config import Config
from app.extensions import db
from app.models import User

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    # Drop all tables
    db.drop_all()
    # Create all tables
    db.create_all()
    
    # Create admin user
    admin = User(username='admin', is_admin=True)
    admin.set_password('admin123')
    db.session.add(admin)
    
    # Create test user
    user = User(username='test')
    user.set_password('test123')
    db.session.add(user)
    
    db.session.commit()
    print("Database initialized with admin and test users created successfully!")
