"""Setup script for initializing the Grow Tracker application."""
import os
import sys
from pathlib import Path

def setup_environment():
    """Create .env file if it doesn't exist."""
    env_path = Path('.env')
    if not env_path.exists():
        with open(env_path, 'w') as f:
            f.write('FLASK_APP=run.py\n')
            f.write('FLASK_ENV=development\n')
            f.write('SECRET_KEY=your-secret-key-here\n')
            f.write('DATABASE_URL=sqlite:///app.db\n')
        print("Created .env file")

def setup_venv():
    """Create and activate virtual environment."""
    if not os.path.exists('venv'):
        os.system('python -m venv venv')
        print("Created virtual environment")
    
    # Activate virtual environment
    if sys.platform == 'win32':
        activate_script = 'venv\\Scripts\\activate'
    else:
        activate_script = 'source venv/bin/activate'
    
    print(f"To activate virtual environment, run: {activate_script}")

def install_requirements():
    """Install required packages."""
    if sys.platform == 'win32':
        pip_path = 'venv\\Scripts\\pip'
    else:
        pip_path = 'venv/bin/pip'
    
    os.system(f'{pip_path} install -r requirements.txt')
    print("Installed requirements")

def init_database():
    """Initialize the database."""
    # Remove existing database
    if os.path.exists('app.db'):
        os.remove('app.db')
        print("Removed existing database")
    
    if sys.platform == 'win32':
        flask_path = 'venv\\Scripts\\flask'
    else:
        flask_path = 'venv/bin/flask'
    
    # Initialize database
    os.system(f'{flask_path} db upgrade')
    print("Initialized database")
    
    # Create admin user
    python_path = 'venv\\Scripts\\python' if sys.platform == 'win32' else 'venv/bin/python'
    os.system(f'{python_path} create_admin.py')
    print("Created admin user")

def main():
    """Run the setup process."""
    print("Starting Grow Tracker setup...")
    
    setup_environment()
    setup_venv()
    install_requirements()
    init_database()
    
    print("\nSetup complete!")
    print("\nDefault admin credentials:")
    print("Username: admin")
    print("Password: admin123")
    print("\nPlease change the admin password after first login!")
    
    print("\nTo start the application:")
    print("1. Activate the virtual environment")
    if sys.platform == 'win32':
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("2. Run the application:")
    print("   python run.py")

if __name__ == '__main__':
    main()
