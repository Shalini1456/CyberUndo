from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy instance
db = SQLAlchemy()

def init_db(app):
    """
    Initialize database connection and auto-create tables for the MVP.
    """
    db.init_app(app)
    with app.app_context():
        # Import models so SQLAlchemy metadata is aware of all tables before create_all
        import models  # noqa: F401
        db.create_all()
