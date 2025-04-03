from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pymysql
# from database import Database
# 调整为异步的数据驱动,同步修改了SQLAlchemy的连接,原来的create_engine是同步连接

DATABASE_URL = "mysql+aiomysql://root:yachi111@localhost/parking_db"
SYNC_DATABASE_URL = "mysql+pymysql://root:yachi111@localhost/parking_db"
# url = mysql =数据库类型，表示我们使用的是MySQL数据库。
# aiomysql 是MySQL的异步驱动程序，支持异步操作，以便与FastAPI兼容。
# username:password
# localhost 是数据库服务器的地址。这里表示数据库在本地运行。如果数据库运行在远程服务器上，可以替换为服务器的IP地址或域名。
# dbname 是要连接的具体数据库的名称

async_engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True   # 这个参数可以确保从连接池获取的连接是可用的，防止因数据库连接超时而引发的问题。
    # encoding,用什么字符编码,echo=True代表启动日志功能,connect_args=是数据库连接传递的参数,check_same_thread=False是多个线程之间共享同一个连接
)

# 创建同步引擎用于初始化数据库表
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=True
)

async_sessionmaker = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
)

Base = declarative_base()
# declarative陈述基类,也就是创建一个基类(base class)
# 创建基类的时候常用参数:
#   1.	bind：绑定数据库引擎 engine。
# 	2.	metadata：使用自定义的元数据对象 custom_metadata。
# 	3.	name：基类名称设置为 MyBase。
# 	4.	constructor：使用自定义构造函数 my_constructor。


async def get_db():
    async with async_sessionmaker() as session:
        try:
            yield session
        finally:
            await session.close()


async def test_connection():
    try:
        async with async_engine.connect() as conn:
            print("数据库连接成功！")
    except Exception as e:
        print(f"数据库连接失败：{e}")

# 运行测试
async def main():
    await test_connection()
    await async_engine.dispose()  # 正确关闭引擎和连接池

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
# 这里的接口是一个同步的接口,如果要使用异步,则需要用到databases
# DATABASE_URL = "mysql+aiomysql://root:yachi111@localhost/parking_db"
#
# database = Database(DATABASE_URL)
# metadata = MetaData()
#
# engine = create_engine(
#     DATABASE_URL, encoding='utf-8', echo=True
# )
#
# SessionLocal = sessionmaker(bind=engine,  # 把会话(session)绑定到之前的数据库引擎
#                             autoflush=False,  # 禁用自动刷新,
#                             autocommit=False,  # 禁用提交事务
#                             expire_on_commit=True  # 启用提交后过期
#                             )
#
# Base = declarative_base()

