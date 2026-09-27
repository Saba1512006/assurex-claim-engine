"""SQLAlchemy handle, table creation and additive column upgrades for existing databases."""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

db = SQLAlchemy()


def _add_missing_columns() -> list[str]:
    """Add new nullable columns to tables that already exist (e.g. a deployed SQLite file), so an upgrade
    never needs the data wiped. Only additive: columns are never dropped or altered."""
    added = []
    insp = inspect(db.engine)
    for table in db.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        have = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name not in have and col.nullable and col.server_default is None:
                ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col.type.compile(db.engine.dialect)}'
                with db.engine.begin() as conn:
                    conn.execute(text(ddl))
                added.append(f"{table.name}.{col.name}")
    return added


def init_db(app):
    """Initialize database with the Flask application context."""
    db.init_app(app)
    with app.app_context():
        import src.models.entities  # noqa: F401  (registers every table)
        db.create_all()
        for column in _add_missing_columns():
            app.logger.info("Database upgraded: added column %s", column)
