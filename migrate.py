from flask import Flask
from flask_migrate import Migrate
from app.extensions import db
from app import create_app

flask_app = create_app()
migrate = Migrate(flask_app, db)

if __name__ == '__main__':
    # This allows running migrations directly
    pass
