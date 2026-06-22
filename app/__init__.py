from flask import Flask


def create_app(config_class="config.Config"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    from app.routes import main_bp

    app.register_blueprint(main_bp)
    return app
