import eventlet
eventlet.monkey_patch()

from app import create_app
from app.extensions import socketio

app = create_app()

if __name__ == '__main__':
    port = 5555
    print(f"Starting server on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
