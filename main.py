import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

from lib.db import init_db, get_latest, get_plant
from lib.api import api
from lib.ws import socketio

from lib.auth import auth as auth_blueprint, login_required
from lib.flash_routes import flash_bp

def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ecoadapt-dev-key")

    CORS(app)
    socketio.init_app(app)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(api)
    app.register_blueprint(flash_bp)

    @app.route("/")
    @login_required
    def index():
        return app.send_static_file("index.html")

    return app

def start_scheduler(app):
    scheduler = BackgroundScheduler()

    def checkin_job():
        with app.app_context():
            from lib.personality import daily_checkin
            from lib.ws import emit_speech
            from lib.thresholds import get_mood

            reading = get_latest()
            if not reading:
                return

            plant = get_plant()
            mood = get_mood(reading, plant.get("species", "pothos"))

            try:
                speech = daily_checkin(reading)
                emit_speech(speech, mood, plant.get("species", "pothos"))
                print(f"Daily checkin: {speech}")
            except Exception as e:
                print(f"Checkin error: {e}")

    # Daily checkin at noon
    scheduler.add_job(checkin_job, "cron", hour=12, minute=0)
    scheduler.start()
    return scheduler

if __name__ == "__main__":
    app = create_app()
    init_db()
    scheduler = start_scheduler(app)

    port = int(os.environ.get("PORT", 5000))
    print(f"EcoAdapt server starting on port {port}")

    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=os.environ.get("DEBUG", "false").lower() == "true",
        allow_unsafe_werkzeug=True
    )
