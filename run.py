import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Pull cloud data ONCE at startup (not inside create_app to avoid double-run with reloader)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        with app.app_context():
            try:
                from app.backup.sync import firebase_to_postgres
                result = firebase_to_postgres()
                synced = result.get('restored', {})
                print(f"[BankSim] Cloud sync on startup: {result.get('status')}")
                for t, c in synced.items():
                    print(f"  {t}: {c} records")
            except Exception as e:
                print(f"[BankSim] Cloud sync skipped: {e}")

    app.run(debug=True, port=5000, use_reloader=True)
