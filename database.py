import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime

Base = declarative_base()

class AstroDailyScore(Base):
    __tablename__ = 'astro_daily_scores'
    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    score = Column(Float, nullable=False)
    bias = Column(String(50), nullable=False)
    nakshatra = Column(String(50))
    tithi = Column(String(50))
    eclipse = Column(String(50))
    numerology_vib = Column(Integer)
    created_at = Column(Date, default=datetime.date.today)

class TopStockTurnDate(Base):
    __tablename__ = 'top_stock_turn_dates'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    ticker = Column(String(20), nullable=False)
    price = Column(Float)
    orb = Column(Float)
    alignment = Column(String(100))

# Set up SQLite database
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'astro_db.sqlite')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)

def get_session():
    return SessionLocal()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
