from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
import bcrypt
from datetime import datetime

from models import User, ParkingLot, Record, RecordStatus
from schemas import UserCreate, ParkingLotSearch, RecordCreate, RecordUpdate, ParkingLotCreate
import logging


# 关于crud文件，首先需要了解到crud文件和main文件的关系
# crud只是一个动作，在稍后的main文件里我们会通过上一层的函数调取这些动作
# 之所以把这些动作分拆写到crud文件里，是为了让整个项目文件清晰，也让代码的重复利用率提高了。
# 创建用户
async def create_user(db: AsyncSession, user: UserCreate):
    # 这里的db并不指定是我们已经创建的数据库,db只是设定需要输入一个异步的Session
    try:
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
        db_user = User(
            username=user.username,
            password=hashed_password.decode('utf-8'),
            role=user.role
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user
    except Exception as e:
        await db.rollback()
        raise e


# 通过用户名读取用户
async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalar()


# 验证密码
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


# 创建停车场
async def create_parking_lot(db: AsyncSession, parking_lot: ParkingLotCreate):
    # 新建停车场需要一个数据库对话写入数据,加上停车场信息,这个信息要符合schemas里面的ParkingLotCreate格式
    try:
        db_parking_lot = ParkingLot(  # models.[类名]
            location=parking_lot.location,   # 从传入函数的parking_lot里面提取对应的数据
            description=parking_lot.description,
            capacity=parking_lot.capacity,
            fee_rate=parking_lot.fee_rate
        )
        db.add(db_parking_lot)   # 将新创建的 db_parking_lot 对象添加到数据库会话中。
        await db.commit()  # 提交
        await db.refresh(db_parking_lot)  # 刷新对象
        return db_parking_lot  # 返回对象
    except SQLAlchemyError as e:
        await db.rollback()   # 如果出现异常,撤销刚才的更改,恢复执行前的状态
        raise e  # 返回错误提示


# 读取所有停车场
async def get_parking_lots(db: AsyncSession, search_criteria: ParkingLotSearch):
    try:
        query = select(ParkingLot)

        # 只在有值且不为空字符串时添加过滤条件
        if search_criteria.location and search_criteria.location.strip():
            query = query.filter(ParkingLot.location.ilike(f"%{search_criteria.location.strip()}%"))
        if search_criteria.name and search_criteria.name.strip():
            query = query.filter(ParkingLot.name.ilike(f"%{search_criteria.name.strip()}%"))
        if search_criteria.id:
            query = query.filter(ParkingLot.id == search_criteria.id)

        # 添加排序
        query = query.order_by(ParkingLot.id)

        result = await db.execute(query)
        return result.scalars().all()
    except Exception as e:
        logging.error(f"Error getting parking lots: {str(e)}")
        raise e


# 读取某个用户的所有记录
async def get_records_by_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(Record).filter(Record.user_id == user_id))
    return result.scalars().all()


# 读取单个停车场的所有记录
async def get_records_by_parking_lot(db: AsyncSession, parking_lot_id: int):
    result = await db.execute(select(Record).filter(Record.parking_lot_id == parking_lot_id))
    return result.scalars().all()


# 读取记录
async def get_record(db: AsyncSession, record_id: int):
    result = await db.execute(select(Record).filter(Record.id == record_id))
    return result.scalar()


# 创建记录
async def create_record(db: AsyncSession, record: RecordCreate, user_id: int):
    try:
        # 检查车牌号是否已经在其他停车场停车
        existing_record = await db.execute(
            select(Record)
            .filter(
                Record.car_number == record.car_number,
                Record.status == RecordStatus.PARKED
            )
        )
        if existing_record.scalar():
            raise ValueError("该车辆已在其他停车场停车")

        # 检查停车场是否存在且有可用空间
        parking_lot = await db.execute(
            select(ParkingLot).filter(ParkingLot.id == record.parking_lot_id)
        )
        parking_lot = parking_lot.scalar()
        
        if not parking_lot:
            raise ValueError("停车场不存在")
        
        if not parking_lot.availability:
            raise ValueError("停车场已满")

        # 创建新记录，确保状态值为大写
        db_record = Record(
            user_id=user_id,
            parking_lot_id=record.parking_lot_id,
            car_number=record.car_number,
            status=RecordStatus.PARKED,  # 直接使用枚举值
            entry_time=datetime.now()
        )
        
        # 更新停车场占用情况
        parking_lot.occupancy += 1
        
        db.add(db_record)
        await db.commit()
        await db.refresh(db_record)
        return db_record
    except Exception as e:
        await db.rollback()
        raise e


# 读取全部 check-in 的记录
async def get_record_checkin(db: AsyncSession):
    result = await db.execute(select(Record).filter(Record.check_out_time == None).order_by(Record.check_in_time.desc()))
    return result.scalars().all()


# 更新记录
async def update_record(db: AsyncSession, record_id: int, record_update: RecordUpdate):
    try:
        # 获取记录
        db_record = await get_record(db, record_id)
        if not db_record:
            raise ValueError("记录不存在")

        # 如果状态变更为已完成，需要计算费用并更新停车场占用情况
        if record_update.status == RecordStatus.COMPLETED and db_record.status != RecordStatus.COMPLETED:
            # 获取停车场
            parking_lot = await db.execute(
                select(ParkingLot).filter(ParkingLot.id == db_record.parking_lot_id)
            )
            parking_lot = parking_lot.scalar()
            
            if not parking_lot:
                raise ValueError("停车场不存在")

            # 设置离开时间
            db_record.exit_time = datetime.now()
            
            # 计算停车时长（小时）
            duration = (db_record.exit_time - db_record.entry_time).total_seconds() / 3600
            
            # 计算费用
            db_record.amount = duration * parking_lot.fee_rate
            
            # 更新停车场占用情况
            parking_lot.occupancy -= 1

        # 更新状态，确保使用枚举值
        db_record.status = record_update.status
        
        await db.commit()
        await db.refresh(db_record)
        return db_record
    except Exception as e:
        await db.rollback()
        raise e


# 读取所有未完成的记录
async def get_uncompleted_records(db: AsyncSession):
    result = await db.execute(
        select(Record)
        .filter(Record.status == RecordStatus.PARKED)
        .order_by(Record.entry_time.desc())
    )
    return result.scalars().all()
