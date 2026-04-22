import os
from flask import Flask, render_template
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from models.models import db
from utils.config import config
from utils.logger import setup_logger
from routes.auth_routes import auth_bp, init_oauth
from routes.main_routes import main_bp
from services.game_service import seed_games
from services.challenge_service import generate_daily_challenges
from services.chat_service import register_socket_events

# Initialize extensions
socketio = SocketIO(cors_allowed_origins="*")
migrate = Migrate()

def create_app(config_name=None):
    """Application factory"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    
    # Register SocketIO events
    register_socket_events(socketio)
    
    # Initialize OAuth
    init_oauth(app)
    
    # Setup logging
    setup_logger(app)
    
    # Rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )
    
    # Security headers (production only)
    if config_name == 'production':
        Talisman(app, force_https=True)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', error='Page not found', code=404), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('error.html', error='Internal server error', code=500), 500
    
    # Initialize database
    with app.app_context():
        db.create_all()
        seed_games()
        generate_daily_challenges()
    
    return app

# Create application instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, debug=False, host='0.0.0.0', port=port)
