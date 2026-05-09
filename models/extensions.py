# models/extensions.py
# We create the db instance here so every model can import it
# without triggering circular imports with app.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
