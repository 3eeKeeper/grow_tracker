"""Create the default admin user."""
import eventlet
eventlet.monkey_patch()

from app import create_app
from app.extensions import db
from app.models import User

def create_admin():
    """Create the default admin user if it doesn't exist."""
    app = create_app()
    
    with app.app_context():
        # Check if admin exists
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print("Admin user already exists")
            return
        
        # Create admin user
        admin = User(
            username='admin',
            is_admin=True
        )
        admin.set_password('admin123')
        
        db.session.add(admin)
        db.session.commit()
        print("Created admin user")

if __name__ == '__main__':
    create_admin()
