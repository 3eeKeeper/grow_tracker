# Cannabis Plant Grow Tracker

A comprehensive web-based application for tracking cannabis plant growth, designed for both individual growers and collaborative growing communities. Built with Flask and modern web technologies, this application provides detailed plant monitoring, growth tracking, and community features.

## Features

### Plant Management
- Create and manage individual plant profiles
- Track growth stages and milestones
- Record watering and nutrient schedules
- Upload and manage plant photos
- Monitor plant health metrics
- Take and organize growing notes

### User System
- Secure user authentication and authorization
- Personal dashboards for each user
- Admin panel for user management
- User profile customization
- Last seen and online status tracking

### Group Growing
- Create and join group grows
- Collaborative plant monitoring
- Share growing tips and experiences
- Follow other growers' plants
- Community interaction features

### Data Tracking
- Growth stage progression
- Watering history
- Nutrient schedules
- Environmental conditions
- Plant measurements
- Health indicators

## Technology Stack

- **Backend**: Python/Flask
- **Database**: SQLAlchemy with SQLite/PostgreSQL
- **Frontend**: Bootstrap 5, JavaScript
- **Authentication**: Flask-Login
- **Real-time Updates**: Flask-SocketIO
- **Image Handling**: PIL/Pillow

## Quick Start

### One-Click Setup

1. Run the setup script:
   ```bash
   python setup.py
   ```

This will:
- Create a virtual environment
- Install all dependencies
- Initialize the database
- Create a default admin user

### Manual Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with:
   ```
   FLASK_APP=run.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=sqlite:///app.db
   ```

4. Initialize the database:
   ```bash
   flask db upgrade
   python create_admin.py
   ```

5. Run the application:
   ```bash
   python run.py
   ```

### Default Admin Credentials
- Username: `admin`
- Password: `admin123`

**Important:** Change the admin password after first login!

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/grow-tracker.git
   cd grow-tracker
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root:
   ```
   FLASK_APP=run.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=sqlite:///app.db
   ```

5. Initialize the database:
   ```bash
   flask db upgrade
   ```

6. Run the application:
   ```bash
   python run.py
   ```

## Development Setup

1. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

3. Run tests:
   ```bash
   pytest
   ```

## Project Structure

```
grow-tracker/
├── app/
│   ├── __init__.py
│   ├── auth/
│   ├── main/
│   ├── models/
│   ├── static/
│   ├── templates/
│   └── utils/
├── migrations/
├── tests/
├── venv/
├── .env
├── .gitignore
├── config.py
├── requirements.txt
└── run.py
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Security Notice

This application is designed for tracking personal or community growing operations where legal. Please ensure compliance with your local regulations regarding cannabis cultivation.
