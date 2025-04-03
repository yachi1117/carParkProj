# This makes the carParking directory a Python package
from .database import Base, get_db
from .models import User, ParkingLot, Record
from .schemas import UserCreate, User, ParkingLot, Record, Token
from carParking.crud import (
    create_user, get_user_by_username, verify_password,
    create_parking_lot, get_parking_lots,
    create_record, get_records_by_user
)