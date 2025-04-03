# 模型类 ,两张数据库的表格
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base

class UserRole(str, enum.Enum):
    customer = "customer"
    admin = "admin"

class RecordStatus(str, enum.Enum):
    PARKED = "PARKED"      # 已停车
    PAID = "PAID"          # 已付款
    COMPLETED = "COMPLETED" # 已完成（已出库）
    
    # 同时支持小写版本
    parked = "PARKED"
    paid = "PAID"
    completed = "COMPLETED"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            # 尝试将值转换为大写并匹配
            upper_value = value.upper()
            for member in cls:
                if member.value == upper_value:
                    return member
        return None

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(100), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.customer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联关系
    records = relationship("Record", back_populates="user")

class ParkingLot(Base):
    __tablename__ = "parking_lots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    location = Column(String(255), nullable=False)
    description = Column(String(255))
    capacity = Column(Integer, nullable=False)
    fee_rate = Column(Float, nullable=False)  # 每小时费用
    occupancy = Column(Integer, default=0)  # 当前占用数量
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联关系
    records = relationship("Record", back_populates="parking_lot")

    @property
    def availability(self):
        return self.occupancy < self.capacity

class Record(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parking_lot_id = Column(Integer, ForeignKey("parking_lots.id"), nullable=False)
    car_number = Column(String(20), nullable=False)  # 车牌号
    entry_time = Column(DateTime(timezone=True), server_default=func.now())
    exit_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(RecordStatus), default=RecordStatus.PARKED)
    amount = Column(Float, default=0.0)  # 停车费用
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联关系
    user = relationship("User", back_populates="records")
    parking_lot = relationship("ParkingLot", back_populates="records")

    def __repr__(self):
        return f"<Record(id={self.id}, user_id={self.user_id}, parking_lot_id={self.parking_lot_id}, car_number={self.car_number}, entry_time={self.entry_time}, exit_time={self.exit_time})>"
