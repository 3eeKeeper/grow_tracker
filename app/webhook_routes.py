from flask import Blueprint, request, jsonify
from app.extensions import db
from app.signal_service import SignalService

bp = Blueprint('webhook', __name__)
signal_service = None

def init_signal_service(app):
    global signal_service
    signal_service = SignalService(
        app.config.get('SIGNAL_BOT_NUMBER'),
        app.config.get('SIGNAL_API_URL')
    )

def verify_signal_signature(signature, payload):
    """Verify webhook signature from Signal"""
    if not current_app.config.get('SIGNAL_WEBHOOK_SECRET'):
        return True  # Skip verification if no secret configured
        
    expected = hmac.new(
        current_app.config['SIGNAL_WEBHOOK_SECRET'].encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

@bp.route('/webhook/signal', methods=['POST'])
def signal_webhook():
    """Handle incoming Signal messages"""
    # Verify webhook signature if provided
    signature = request.headers.get('X-Signal-Signature')
    if signature and not verify_signal_signature(signature, request.get_data()):
        return jsonify({'error': 'Invalid signature'}), 401

    if not signal_service:
        return jsonify({"error": "Signal service not initialized"}), 500
        
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400
        
    sender = data.get('sender')
    message = data.get('message')
    
    if not sender or not message:
        return jsonify({"error": "Missing sender or message"}), 400
        
    response = signal_service.process_incoming_message(sender, message)
    return jsonify(response)
