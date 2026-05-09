import psycopg2
from flask import current_app, g

def get_db_conn():
    if 'db_conn' not in g:
        try:
            g.db_conn = psycopg2.connect(
                dbname=current_app.config['POSTGRES_DB'],
                user=current_app.config['POSTGRES_USER'],
                password=current_app.config['POSTGRES_PASSWORD'],
                host=current_app.config['POSTGRES_HOST'],
                port=current_app.config['POSTGRES_PORT']
            )
        except psycopg2.Error as e:
            current_app.logger.error(f"Database connection failed: {e}")
            raise e
    return g.db_conn

def close_db_conn(e=None):
    db_conn = g.pop('db_conn', None)
    if db_conn is not None:
        db_conn.close()

def init_app(app):
    app.teardown_appcontext(close_db_conn)
