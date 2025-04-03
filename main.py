from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.future import select
import logging
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
import bcrypt
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from datetime import datetime
from typing import List
from sqlalchemy import text

from database import get_db, sync_engine, Base, async_sessionmaker
from models import User as ModelUser, ParkingLot as ModelParkingLot, Record as ModelRecord, UserRole, RecordStatus
from schemas import (
    UserCreate, User as SchemaUser, ParkingLotSearch, Token,
    ParkingLot, RecordCreate, Record, RecordUpdate, ParkingLotCreate
)
import crud

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 使用同步引擎创建数据库表
Base.metadata.create_all(bind=sync_engine)

# 配置FastAPI应用
app = FastAPI()

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 配置CORS
origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*", "Set-Cookie"],
    max_age=3600,
)

# 设置会话中间件
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key-here",
    session_cookie="session",
    same_site="lax",  # 改为lax以提高安全性
    https_only=False,  # 开发环境设置为False
    max_age=3600  # 会话有效期1小时
)


# async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
#     user_id = request.session.get("user_id")
#     if not user_id:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
#     result = await db.execute(select(ModelUser).filter(ModelUser.id == user_id))  # 使用 await 关键字调用异步操作
#     user = result.scalar()
#     if not user:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
#     return user


@app.post("/auth/register", response_model=SchemaUser)
async def register(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        # 获取请求数据
        form_data = await request.json()
        logging.info(f"Received register request with data: {form_data}")

        # 验证用户数据
        try:
            user_data = UserCreate(**form_data)
        except ValidationError as e:
            logging.error(f"Validation error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(e)}
            )

        # 检查用户名是否已存在
        db_user = await crud.get_user_by_username(db, username=user_data.username)
        if db_user:
            logging.error(f"Username already registered: {user_data.username}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Username already registered"}
            )

        # 创建新用户
        try:
            new_user = await crud.create_user(db=db, user=user_data)
            logging.info(f"User {user_data.username} registered successfully")
            return new_user
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Database error occurred"}
            )

    except Exception as e:
        logging.error(f"Unexpected error in register: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred"}
        )


@app.post("/auth/login", response_model=SchemaUser)
async def login(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        form_data = await request.json()
        username = form_data.get('username')
        password = form_data.get('password')
        
        logging.info(f"Login attempt for user: {username}")
        
        if not username or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username and password are required"
            )

        db_user = await crud.get_user_by_username(db, username=username)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        if not crud.verify_password(password, db_user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # 创建会话
        request.session.clear()  # 清除旧会话
        session_data = {
            "user_id": db_user.id,
            "username": db_user.username,
            "role": db_user.role,
            "login_time": str(datetime.now())
        }
        request.session.update(session_data)
        
        logging.info(f"User {username} logged in successfully. Session data: {dict(request.session)}")
        
        # 返回用户信息，确保日期时间字段不为空
        current_time = datetime.now()
        response_data = SchemaUser(
            id=db_user.id,
            username=db_user.username,
            password=db_user.password,  # 这个字段在实际应用中应该被移除
            role=db_user.role,
            created_at=db_user.created_at or current_time,
            updated_at=db_user.updated_at or current_time
        )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Successfully logged out"}


@app.get("/parking/lots", response_model=list[ParkingLot])
async def get_parking_lots(
    location: str = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        # 创建搜索条件
        search_criteria = ParkingLotSearch(location=location)
        
        # 获取停车场列表
        parking_lots = await crud.get_parking_lots(db=db, search_criteria=search_criteria)
        
        # 确保返回的是列表
        if not isinstance(parking_lots, list):
            parking_lots = [parking_lots] if parking_lots else []
            
        return parking_lots
    except SQLAlchemyError as e:
        logging.error(f"Database error getting parking lots: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="数据库错误，请稍后重试"
        )
    except Exception as e:
        logging.error(f"Error getting parking lots: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# 权限检查函数
async def check_admin(request: Request):
    user_role = request.session.get("user_role")
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized as admin"
        )


# 管理员修改停车场信息
@app.put("/admin/parkinglots/{parking_lot_id}", response_model=ParkingLot)
async def update_parking_lot(
    parking_lot_id: int,
    parking_lot_update: ParkingLotCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        # 检查管理员权限
        await check_admin(request)

        # 获取停车场
        parking_lot = await db.execute(
            select(ModelParkingLot).filter(ModelParkingLot.id == parking_lot_id)
        )
        parking_lot = parking_lot.scalar()
        if not parking_lot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parking lot not found"
            )

        # 更新停车场信息
        for field, value in parking_lot_update.dict(exclude_unset=True).items():
            setattr(parking_lot, field, value)

        await db.commit()
        await db.refresh(parking_lot)
        return parking_lot
    except Exception as e:
        logging.error(f"Error updating parking lot: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# 管理员查看所有停车记录
@app.get("/admin/records", response_model=list[Record])
async def get_all_records(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        # 检查管理员权限
        await check_admin(request)

        # 获取所有记录
        result = await db.execute(select(ModelRecord))
        records = result.scalars().all()
        return records
    except Exception as e:
        logging.error(f"Error getting all records: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# 修改现有的用户端点，添加权限检查
@app.get("/customer/records", response_model=list[Record])
async def get_user_records(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        # 获取当前用户ID
        user_id = request.session.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )

        # 获取用户的停车记录
        records = await crud.get_records_by_user(db=db, user_id=user_id)
        return records
    except Exception as e:
        logging.error(f"Error getting user records: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/customer/records", response_model=Record)
async def create_parking_record(
    record: RecordCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        # 获取当前用户ID
        user_id = request.session.get("user_id")
        logging.info(f"创建停车记录，用户ID: {user_id}，数据: {record.dict()}")
        
        if not user_id:
            logging.warning("会话中未找到用户ID")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未登录，请先登录"
            )

        # 验证停车场是否存在 - 使用原生SQL
        parking_lot_query = """
        SELECT id, name, location, description, capacity, fee_rate, occupancy
        FROM parking_lots
        WHERE id = :parking_lot_id
        """
        result = await db.execute(text(parking_lot_query), {"parking_lot_id": record.parking_lot_id})
        parking_lot = result.fetchone()
        
        if not parking_lot:
            logging.error(f"停车场 {record.parking_lot_id} 不存在")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="停车场不存在"
            )

        # 检查停车场是否已满
        if parking_lot.occupancy >= parking_lot.capacity:
            logging.warning(f"停车场 {record.parking_lot_id} 已满")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="停车场已满"
            )

        # 检查用户是否有未完成的停车记录 - 使用原生SQL
        active_record_query = """
        SELECT id FROM records
        WHERE user_id = :user_id
        AND UPPER(status) IN ('PARKED')
        """
        active_result = await db.execute(text(active_record_query), {"user_id": user_id})
        if active_result.fetchone():
            logging.warning(f"用户 {user_id} 已有一个进行中的停车记录")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="您已有一个正在进行的停车记录"
            )

        try:
            # 更新停车场占用情况 - 使用原生SQL
            new_occupancy = parking_lot.occupancy + 1
            update_parking_lot_query = """
            UPDATE parking_lots
            SET occupancy = :occupancy
            WHERE id = :id
            """
            await db.execute(
                text(update_parking_lot_query),
                {
                    "occupancy": new_occupancy,
                    "id": parking_lot.id
                }
            )
            
            # 创建停车记录 - 使用原生SQL (MySQL兼容版本)
            entry_time = datetime.now()
            create_record_query = """
            INSERT INTO records (user_id, car_number, parking_lot_id, entry_time, status, amount)
            VALUES (:user_id, :car_number, :parking_lot_id, :entry_time, :status, :amount)
            """
            insert_result = await db.execute(
                text(create_record_query),
                {
                    "user_id": user_id,
                    "car_number": record.car_number,
                    "parking_lot_id": record.parking_lot_id,
                    "entry_time": entry_time,
                    "status": "PARKED",
                    "amount": 0.0
                }
            )
            
            # 获取最后插入的ID - MySQL特有方法
            get_last_id_query = "SELECT LAST_INSERT_ID() as id"
            last_id_result = await db.execute(text(get_last_id_query))
            record_id = last_id_result.scalar_one()
            
            await db.commit()
            
            logging.info(f"成功创建停车记录: ID {record_id}")
            
            # 将记录转换为字典并返回
            return {
                "id": record_id,
                "user_id": user_id,
                "car_number": record.car_number,
                "parking_lot_id": record.parking_lot_id,
                "status": "PARKED",
                "entry_time": entry_time,
                "exit_time": None,
                "amount": 0.0
            }

        except SQLAlchemyError as e:
            await db.rollback()
            logging.error(f"创建停车记录时发生数据库错误: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="数据库错误，请稍后重试"
            )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"创建停车记录时发生未知错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建停车记录时发生错误"
        )


@app.put("/customer/records/{record_id}", response_model=Record)
async def update_record(
    record_id: int,
    record_update: RecordUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        # 获取当前用户ID
        user_id = request.session.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未登录，请先登录"
            )

        logging.info(f"更新记录 {record_id}，状态: {record_update.status}，用户ID: {user_id}")

        # 获取记录 - 使用直接的SQL查询，避免枚举问题
        query = """
        SELECT id, user_id, car_number, parking_lot_id, 
               status, entry_time, exit_time, amount
        FROM records 
        WHERE id = :record_id
        """
        result = await db.execute(text(query), {"record_id": record_id})
        record_row = result.fetchone()
        
        if not record_row:
            logging.warning(f"记录 {record_id} 不存在")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="记录不存在"
            )
            
        # 检查记录是否属于当前用户
        if record_row.user_id != user_id:
            logging.warning(f"用户 {user_id} 无权修改记录 {record_id}，该记录属于用户 {record_row.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限修改此记录"
            )

        # 如果状态变更为已完成，需要计算费用并更新停车场占用情况
        try:
            logging.info(f"当前记录状态: {record_row.status}, 目标状态: {record_update.status}")
            
            # 确保使用大写的字符串
            target_status = record_update.status.upper()
            current_status = str(record_row.status).upper()
            
            if current_status != target_status:
                logging.info(f"状态将从 {current_status} 变为 {target_status}")
                
                # 获取停车场
                parking_lot_query = """
                SELECT id, name, location, description, capacity, fee_rate, occupancy
                FROM parking_lots
                WHERE id = :parking_lot_id
                """
                parking_lot_result = await db.execute(
                    text(parking_lot_query), 
                    {"parking_lot_id": record_row.parking_lot_id}
                )
                parking_lot = parking_lot_result.fetchone()
                
                if not parking_lot:
                    logging.warning(f"停车场 {record_row.parking_lot_id} 不存在")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="停车场不存在"
                    )
                
                logging.info(f"找到停车场 {parking_lot.id}, 当前占用: {parking_lot.occupancy}")

                # 设置离开时间
                exit_time = datetime.now()
                
                # 计算停车时长（小时）
                duration = (exit_time - record_row.entry_time).total_seconds() / 3600
                
                # 计算费用
                amount = duration * parking_lot.fee_rate
                
                # 更新停车场占用情况
                new_occupancy = max(0, parking_lot.occupancy - 1)
                
                await db.execute(
                    text("""
                    UPDATE parking_lots
                    SET occupancy = :occupancy
                    WHERE id = :id
                    """),
                    {
                        "occupancy": new_occupancy,
                        "id": parking_lot.id
                    }
                )
                
                logging.info(f"更新后的停车场占用: {new_occupancy}, 停车时长: {duration}小时, 费用: {amount}")

                # 更新记录
                await db.execute(
                    text("""
                    UPDATE records
                    SET status = :status,
                        exit_time = :exit_time,
                        amount = :amount
                    WHERE id = :id
                    """),
                    {
                        "status": target_status,
                        "exit_time": exit_time,
                        "amount": amount,
                        "id": record_id
                    }
                )
            else:
                # 只更新状态
                await db.execute(
                    text("""
                    UPDATE records
                    SET status = :status
                    WHERE id = :id
                    """),
                    {
                        "status": target_status,
                        "id": record_id
                    }
                )
            
            await db.commit()
            
            # 获取更新后的记录
            updated_record_query = """
            SELECT id, user_id, car_number, parking_lot_id, 
                   status, entry_time, exit_time, amount
            FROM records 
            WHERE id = :record_id
            """
            updated_result = await db.execute(text(updated_record_query), {"record_id": record_id})
            updated_record = updated_result.fetchone()
            
            logging.info(f"成功更新记录 {updated_record.id}, 新状态: {updated_record.status}")
            
            # 将记录转换为字典并返回
            return {
                "id": updated_record.id,
                "user_id": updated_record.user_id,
                "car_number": updated_record.car_number,
                "parking_lot_id": updated_record.parking_lot_id,
                "status": target_status,
                "entry_time": updated_record.entry_time,
                "exit_time": updated_record.exit_time,
                "amount": updated_record.amount
            }
            
        except SQLAlchemyError as e:
            await db.rollback()
            logging.error(f"更新记录 {record_id} 时发生数据库错误: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="数据库错误，请稍后重试"
            )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"更新记录 {record_id} 时发生未知错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新记录时发生错误"
        )


@app.get("/customer/records/uncompleted", response_model=list[Record])
async def get_uncompleted_records(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        # 获取当前用户ID
        user_id = request.session.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )

        # 获取未完成的记录
        records = await crud.get_uncompleted_records(db=db)
        return records
    except Exception as e:
        logging.error(f"Error getting uncompleted records: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/customer/my-records", response_model=List[Record])
async def get_my_records(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        # 获取当前用户ID
        user_id = request.session.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未登录，请先登录"
            )

        logging.info(f"正在获取用户 {user_id} 的停车记录")

        try:
            # 使用直接的SQL查询
            query = """
            SELECT id, user_id, car_number, parking_lot_id, 
                   UPPER(status) as status, entry_time, exit_time, amount,
                   created_at, updated_at
            FROM records 
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            """
            result = await db.execute(text(query), {"user_id": user_id})
            rows = result.fetchall()
            
            logging.info(f"成功获取到 {len(rows)} 条停车记录")
            
            # 将行转换为字典
            records = []
            for row in rows:
                record_dict = {
                    "id": row.id,
                    "user_id": row.user_id,
                    "car_number": row.car_number,
                    "parking_lot_id": row.parking_lot_id,
                    "status": row.status,
                    "entry_time": row.entry_time,
                    "exit_time": row.exit_time,
                    "amount": row.amount
                }
                records.append(record_dict)
            
            return records

        except SQLAlchemyError as e:
            logging.error(f"查询停车记录时发生数据库错误: {str(e)}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="查询数据库时发生错误"
            )

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"获取停车记录时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/")
async def root():
    return FileResponse("static/index.html", media_type="text/html")


# 初始化管理员用户
async def init_admin_user(db: AsyncSession):
    try:
        # 检查是否已存在管理员用户
        admin = await db.execute(
            select(ModelUser).filter(ModelUser.username == "admin")
        )
        admin = admin.scalar()
        
        if not admin:
            # 创建管理员用户
            hashed_password = bcrypt.hashpw("adminpass".encode('utf-8'), bcrypt.gensalt())
            admin_user = ModelUser(
                username="admin",
                password=hashed_password.decode('utf-8'),
                role="admin"
            )
            db.add(admin_user)
            await db.commit()
            logging.info("Admin user created successfully")
    except Exception as e:
        logging.error(f"Error creating admin user: {str(e)}")
        raise


# 初始化停车场数据
async def init_parking_lots(db: AsyncSession):
    try:
        # Check if parking lots already exist
        result = await db.execute(select(ModelParkingLot))
        existing_lots = result.scalars().all()
        
        if not existing_lots:
            # Create test parking lots
            test_lots = [
                ModelParkingLot(
                    name="Downtown Parking A",
                    location="123 Main Street, Downtown",
                    description="24/7 Secure parking near subway station",
                    capacity=100,
                    fee_rate=10.0,
                    occupancy=30
                ),
                ModelParkingLot(
                    name="Business District Parking B",
                    location="456 Commerce Ave, Business District",
                    description="Premium parking with EV charging stations",
                    capacity=200,
                    fee_rate=15.0,
                    occupancy=80
                ),
                ModelParkingLot(
                    name="Shopping Mall Parking C",
                    location="789 Retail Road, Shopping District",
                    description="Covered parking with direct mall access",
                    capacity=300,
                    fee_rate=8.0,
                    occupancy=150
                )
            ]
            
            for lot in test_lots:
                db.add(lot)
            
            await db.commit()
            logging.info("Test parking lots created successfully")
    except Exception as e:
        logging.error(f"Error creating test parking lots: {str(e)}")
        await db.rollback()
        raise


# 在应用启动时初始化数据
@app.on_event("startup")
async def startup_event():
    try:
        # 初始化数据库
        Base.metadata.create_all(bind=sync_engine)
        logging.info("数据库表已创建")
        
        # 修复记录状态值
        async with async_sessionmaker() as db:
            try:
                # 更新所有小写的状态值为大写
                await db.execute(text("""
                    UPDATE records 
                    SET status = CASE 
                        WHEN LOWER(status) = 'parked' THEN 'PARKED'
                        WHEN LOWER(status) = 'paid' THEN 'PAID'
                        WHEN LOWER(status) = 'completed' THEN 'COMPLETED'
                        ELSE status
                    END
                    WHERE LOWER(status) IN ('parked', 'paid', 'completed')
                """))
                await db.commit()
                logging.info("成功修复记录状态值")
            except Exception as e:
                logging.error(f"修复记录状态值时发生错误: {str(e)}")
                await db.rollback()
                raise

        # 初始化管理员用户和停车场
        async with async_sessionmaker() as db:
            await init_admin_user(db)
            await init_parking_lots(db)
            
    except Exception as e:
        logging.error(f"启动事件发生错误: {str(e)}")
        raise


@app.get("/auth/status", response_model=SchemaUser)
async def get_auth_status(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        # 获取当前用户ID
        user_id = request.session.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )

        # 获取用户信息
        result = await db.execute(select(ModelUser).filter(ModelUser.id == user_id))
        user = result.scalar()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # 确保日期时间字段不为空
        current_time = datetime.now()
        return SchemaUser(
            id=user.id,
            username=user.username,
            password=user.password,
            role=user.role,
            created_at=user.created_at or current_time,
            updated_at=user.updated_at or current_time
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error checking auth status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="debug")
    # 用uvicorn运行Fastapi应用,host是可用的主机地址,port是端口的编号
    # 这段代码始终在main.py的末尾
