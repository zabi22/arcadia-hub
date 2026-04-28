import os
from flask import Flask, render_template, request, abort
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from src.models.models import db
from src.utils.config import config
from src.utils.logger import setup_logger
from src.routes.auth_routes import auth_bp, init_oauth
from src.routes.main_routes import main_bp
from src.services.game_service import seed_games
from src.services.challenge_service import generate_daily_challenges
from src.services.chat_service import register_socket_events
from src.services.multiplayer_service import register_multiplayer_events # New import


socketio = SocketIO(
    cors_allowed_origins=[
        os.environ.get('FRONTEND_URL', 'http://localhost:5000'),
        os.environ.get('DOMAIN', 'localhost:5000')
    ],
    async_mode='gevent',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1000000,
    logger=False,
    engineio_logger=False,
    transports=['websocket', 'polling']
)
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
    try:
        register_socket_events(socketio)
        register_multiplayer_events(socketio) # Register multiplayer events
    except Exception as e:
        app.logger.error(f"Failed to register socket events: {e}")

    # Initialize OAuth
    try:
        init_oauth(app)
    except Exception as e:
        app.logger.error(f"OAuth init failed: {e}")

    # Setup logging
    setup_logger(app)

    # Rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["100 per minute", "200 per day", "50 per hour"],
        storage_uri=os.environ.get('REDIS_URL', 'memory://')
    )

    # Security headers (production only)
    if config_name == 'production':
        # Added basic CSP that allows for WebSockets and local assets
        csp = {
            'default-src': '\'self\'',
            'script-src': ['\'self\'', '\'unsafe-inline\'', 'https://cdn.jsdelivr.net'],
            'style-src': ['\'self\'', '\'unsafe-inline\'', 'https://cdn.jsdelivr.net'],
            'connect-src': ['\'self\'', 'ws:', 'wss:']
        }
        Talisman(
            app, 
            force_https=True,
            content_security_policy=csp,
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,  # 1 year
            x_frame_options='DENY',
            x_content_type_options='nosniff',
            referrer_policy='strict-origin-when-cross-origin'
        )
    
    @app.before_request
    def validate_post_content_type():
        """Validate Content-Type for POST/PUT requests to API"""
        if request.method in ['POST', 'PUT'] and request.path.startswith('/api/'):
            content_type = request.headers.get('Content-Type', '')
            if 'application/json' not in content_type and 'multipart/form-data' not in content_type:
                abort(415, description="Unsupported Media Type: application/json or multipart/form-data required")

    # Add security headers middleware (all environments)
    @app.after_request
    def add_security_headers(response):
        """Add additional security headers to all responses"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', error='Page not found', code=404), 404

    @app.errorhandler(415)
    def unsupported_media_type_error(error):
        return render_template('error.html', error=str(error.description), code=415), 415

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f"500 error: {error}")
        return render_template('error.html', error='Internal server error', code=500), 500

    # Initialize database
    with app.app_context():
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'users' not in inspector.get_table_names():
                db.create_all()
            seed_games()
            generate_daily_challenges()
        except Exception as e:
            app.logger.error(f"DB init failed: {e}")
            db.session.rollback()

    return app

# Create application instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    try:
        socketio.run(app, debug=False, host='0.0.0.0', port=port)
    except OSError as e:
        print(f"Error: Port {port} is already in use. Try killing the existing process or use a different PORT environment variable.")
        exit(1)