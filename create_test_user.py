from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

with app.app_context():
    # Check if test user already exists
    if not User.query.filter_by(username='test').first():
        # Create test user
        user = User(username='test')
        user.set_password('test123')
        db.session.add(user)
        db.session.commit()
        print("Test user created successfully!")
    else:
        print("Test user already exists!")
