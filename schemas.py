from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
import enum
from models import UserRole, RecordStatus


# 这个文件的核心功能就是定义不同场景需要的数据项和格式要求
# 所以首先需要的是pydantic库
# 定义用户类型的枚举
class UserType(str, enum.Enum):
    CUSTOMER = "Customer"
    ADMIN = "Admin"


# 用户基础模型
# 这个在注册的时候用,是输入需要的格式,后续对输入的要求用这个类
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True  # 替换 orm_mode = True


class UserBase(BaseSchema):
    username: str


# password是内部保留的,避免调取用户信息的时候被调取,单独用一个pydantic类,后续更新数据库内容的时候用这个类
# 用户创建模型
class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.customer


# id是自动生成的,所以我们用另外一个类储存并生成这个id,这个类是我们后面调取user信息的时候用的类
# 用户响应模型
class User(UserBase):
    id: int
    role: UserRole
    created_at: datetime
    updated_at: datetime


# 停车场基础模型
# 和user一样,先用一个类定义生成实例的时候需要的数据格式
class ParkingLotBase(BaseSchema):
    name: str
    location: str
    description: str
    capacity: int
    fee_rate: float


# 停车场创建模型
# 其实因为停车场没有password这样不显示的数据,所以内容是一样的,但是保持表达的统一和便于理解还是集成基础类型
class ParkingLotCreate(ParkingLotBase):
    pass


# 停车场响应模型,同样是生成自动的id
class ParkingLot(ParkingLotBase):
    id: int
    availability: bool
    created_at: datetime
    updated_at: datetime


# 为了crud里面搜索清晰,我们直接做一个类用来搜索,这里是一个输入格式,所以是一个基类
class ParkingLotSearch(BaseSchema):
    id: Optional[int] = None
    name: Optional[str] = None
    location: Optional[str] = None


# 记录基础模型
class RecordBase(BaseSchema):
    car_number: str
    parking_lot_id: int


# 记录创建模型
class RecordCreate(RecordBase):
    status: Optional[str] = "PARKED"  # 使用字符串而非枚举


# 记录响应模型
class Record(RecordBase):
    id: int
    user_id: int
    status: str  # 使用字符串而非枚举
    entry_time: datetime
    exit_time: Optional[datetime] = None
    amount: Optional[float] = None
    
    @validator('status')
    def validate_status(cls, v):
        if v and isinstance(v, str):
            # 返回字符串的大写形式
            return v.upper()
        return v


# 为了实现针对用户checkin的情况修改页面表达,增加一个特有的类,返回
class RecordUpdate(BaseSchema):
    status: str = "COMPLETED"  # 使用字符串而非枚举


# 认证相关
class Token(BaseSchema):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None