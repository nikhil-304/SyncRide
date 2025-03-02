# SyncRide: Synchronizing rides for seamless travel.

A web-based vehicle pooling system designed specifically for college communities. This application facilitates carpooling among students, making transportation more efficient, cost-effective, and environmentally friendly.

## Features

- User authentication with email verification
- Role-based access (Rider/Traveler)
- Interactive maps for ride sharing
- Real-time notifications
- Profile management
- Ride history tracking
- Rating and feedback system
- Environmental impact tracking

## Tech Stack

- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Backend**: Flask (Python)
- **Database**: SQLite
- **Maps**: Leaflet.js
- **Real-time Updates**: Flask-SocketIO

## Setup Instructions

1. Clone the repository
```bash
git clone [repository-url]
cd SyncRide
```

2. Create and activate a virtual environment
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
Create a `.env` file in the root directory with the following variables:
```
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-email-password
```

5. Initialize the database
```bash
flask db init
flask db migrate
flask db upgrade
```

6. Run the application
```bash
flask run
```

The application will be available at `http://localhost:5000`

## Contributing

Please read our contributing guidelines before submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
