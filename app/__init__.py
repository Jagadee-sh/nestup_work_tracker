from flask import Flask
from .models import db
from .routes import main
from .seed import ensure_seed_data


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'nestup-demo-secret'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nestup.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()
        ensure_seed_data()

    return app
