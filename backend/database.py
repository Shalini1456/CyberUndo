from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

# Initialize SQLAlchemy instance
db = SQLAlchemy()

def init_db(app):
    """
    Initialize database connection and auto-create/update tables for CyberUndo.
    """
    db.init_app(app)
    with app.app_context():
        import models  # noqa: F401
        db.create_all()

        # Safe SQLite column migration for backward compatibility
        if db.engine.name == "sqlite":
            try:
                inspector = inspect(db.engine)
                if "shared_access" in inspector.get_table_names():
                    existing_cols = [c["name"] for c in inspector.get_columns("shared_access")]
                    migrations = [
                        ("recipient_email", "VARCHAR(120)"),
                        ("allow_download", "BOOLEAN DEFAULT 1"),
                        ("expiry_option", "VARCHAR(20) DEFAULT 'never'"),
                        ("view_count", "INTEGER DEFAULT 0"),
                        ("download_count", "INTEGER DEFAULT 0"),
                        ("first_viewed_at", "DATETIME"),
                        ("last_download_at", "DATETIME")
                    ]
                    for col_name, col_type in migrations:
                        if col_name not in existing_cols:
                            db.session.execute(text(f"ALTER TABLE shared_access ADD COLUMN {col_name} {col_type}"))
                    db.session.commit()
            except Exception as e:
                db.session.rollback()
                app.logger.warning(f"Database migration check notice: {e}")

