from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_session import Session
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
session = Session()
csrf = CSRFProtect() 