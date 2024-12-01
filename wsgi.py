from app import create_app, db
from flask_migrate import Migrate

# Create the Flask application
app = create_app()

# Initialize Migrate within the app context
with app.app_context():
    migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run()
