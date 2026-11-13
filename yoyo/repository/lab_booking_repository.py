import random
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import AsyncIterator

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.clients import database_client
from yoyo.models.base import Base
from yoyo.models.lab_booking import BookingRecord, LabRecord

# 预约状态：待到馆 / 使用中 / 已完成 / 已取消
ACTIVE_BOOKING_STATUSES = ("待到馆", "使用中")

# 初始化用的示例实验室
SEED_LABS = [
    {"lab_code": "LAB-201", "name": "电子电路实验室", "capacity": 36, "location": "信息楼2层201",
     "status": "可预约", "open_hours": "08:00-22:00", "description": "模拟电路与数字电路实验，配 36 个实验工位和示波器、信号源。"},
    {"lab_code": "LAB-301", "name": "计算机基础实验室", "capacity": 40, "location": "图书馆A座3层301",
     "status": "可预约", "open_hours": "08:00-22:30", "description": "公共上机实验室，可做程序设计、数据结构等课程实验。"},
    {"lab_code": "LAB-302", "name": "网络工程实验室", "capacity": 30, "location": "图书馆A座3层302",
     "status": "可预约", "open_hours": "08:00-22:00", "description": "配路由器、交换机与网络仿真环境，支持组网与安全实验。"},
    {"lab_code": "LAB-305", "name": "人工智能实验室", "capacity": 24, "location": "图书馆A座3层305",
     "status": "已满", "open_hours": "09:00-21:00", "description": "配 GPU 工作站 24 台，用于深度学习与模型训练实验。"},
    {"lab_code": "LAB-401", "name": "嵌入式实验室", "capacity": 20, "location": "信息楼4层401",
     "status": "可预约", "open_hours": "08:30-21:30", "description": "嵌入式开发板与调试设备齐全，支持单片机、物联网方向实验。"},
    {"lab_code": "LAB-402", "name": "多媒体创作实验室", "capacity": 16, "location": "信息楼4层402",
     "status": "维护中", "open_hours": "09:00-20:00", "description": "图形工作站与音视频采集设备，用于多媒体创作与剪辑。"},
]

# 初始化用的示例预约（学号 + 实验室编号 + 日期 + 时间段）
SEED_BOOKINGS = [
    {"student_no": "20230101", "lab_code": "LAB-301", "booking_date": "2026-11-14",
     "time_slot": "14:00-16:00", "status": "待到馆", "purpose": "数据结构课程实验"},
    {"student_no": "20230101", "lab_code": "LAB-305", "booking_date": "2026-11-12",
     "time_slot": "09:00-11:00", "status": "已完成", "purpose": "深度学习模型训练"},
    {"student_no": "20230102", "lab_code": "LAB-302", "booking_date": "2026-11-13",
     "time_slot": "16:00-18:00", "status": "使用中", "purpose": "组网实验"},
    {"student_no": "20230144", "lab_code": "LAB-401", "booking_date": "2026-11-15",
     "time_slot": "10:00-12:00", "status": "待到馆", "purpose": "嵌入式课程设计"},
    {"student_no": "20220208", "lab_code": "LAB-201", "booking_date": "2026-11-11",
     "time_slot": "19:00-21:00", "status": "已取消", "purpose": "电路实验补做"},
    {"student_no": "20220208", "lab_code": "LAB-301", "booking_date": "2026-11-16",
     "time_slot": "08:00-10:00", "status": "待到馆", "purpose": "程序设计上机"},
]


class LabBookingRepository:
    """实验室与预约的数据访问层"""

    def __init__(self, session: AsyncSession):
        self.session = session

    @classmethod
    @asynccontextmanager
    async def open(cls) -> AsyncIterator["LabBookingRepository"]:
        """在非请求上下文（Action / Provider）中打开一个短事务"""
        async with database_client.session_factory() as session:
            yield cls(session)

    # ---------- 实验室 ----------

    async def get_lab(self, lab_code: str) -> dict | None:
        if not lab_code:
            return None
        sql = select(LabRecord).where(LabRecord.lab_code == lab_code.strip().upper())
        record = (await self.session.execute(sql)).scalar_one_or_none()
        if not record:
            return None
        return await self._lab_to_dict(record)

    async def list_labs(self, status: str | None = None) -> list[dict]:
        sql = select(LabRecord).order_by(LabRecord.lab_code)
        if status:
            sql = sql.where(LabRecord.status == status)
        records = (await self.session.execute(sql)).scalars().all()
        return [await self._lab_to_dict(record) for record in records]

    # ---------- 预约 ----------

    async def get_booking(self, booking_no: str) -> dict | None:
        if not booking_no:
            return None
        sql = select(BookingRecord).where(BookingRecord.booking_no == booking_no.strip().upper())
        record = (await self.session.execute(sql)).scalar_one_or_none()
        if not record:
            return None
        return await self._booking_to_dict(record)

    async def list_bookings_by_student(self, student_no: str) -> list[dict]:
        sql = (
            select(BookingRecord)
            .where(BookingRecord.student_no == student_no.strip())
            .order_by(BookingRecord.booking_date.desc())
        )
        records = (await self.session.execute(sql)).scalars().all()
        return [await self._booking_to_dict(record) for record in records]

    async def create_booking(self, student_no: str, lab_code: str, booking_date: date,
                             time_slot: str, purpose: str = "") -> dict:
        booking_no = await self._next_booking_no()
        record = BookingRecord(
            booking_no=booking_no,
            student_no=student_no.strip(),
            lab_code=lab_code.strip().upper(),
            booking_date=booking_date,
            time_slot=time_slot,
            status="待到馆",
            purpose=purpose,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return await self._booking_to_dict(record)

    async def cancel_booking(self, booking_no: str) -> dict | None:
        sql = select(BookingRecord).where(BookingRecord.booking_no == booking_no.strip().upper())
        record = (await self.session.execute(sql)).scalar_one_or_none()
        if not record:
            return None
        record.status = "已取消"
        await self.session.commit()
        await self.session.refresh(record)
        return await self._booking_to_dict(record)

    async def count_booked(self, lab_code: str, booking_date: date, time_slot: str) -> int:
        """统计同一实验室、同一时段已被占用的名额"""
        sql = select(func.count(BookingRecord.id)).where(
            BookingRecord.lab_code == lab_code.strip().upper(),
            BookingRecord.booking_date == booking_date,
            BookingRecord.time_slot == time_slot,
            BookingRecord.status.in_(ACTIVE_BOOKING_STATUSES),
        )
        return int((await self.session.execute(sql)).scalar() or 0)

    async def count_active_today(self, lab_code: str) -> int:
        sql = select(func.count(BookingRecord.id)).where(
            BookingRecord.lab_code == lab_code.strip().upper(),
            BookingRecord.booking_date == date.today(),
            BookingRecord.status.in_(ACTIVE_BOOKING_STATUSES),
        )
        return int((await self.session.execute(sql)).scalar() or 0)

    # ---------- 内部方法 ----------

    async def _next_booking_no(self) -> str:
        prefix = f"B{datetime.now():%Y%m%d}"
        sql = select(func.count(BookingRecord.id)).where(BookingRecord.booking_no.like(f"{prefix}%"))
        seq = int((await self.session.execute(sql)).scalar() or 0) + 1
        while True:
            booking_no = f"{prefix}{seq:03d}"
            exists = await self.session.execute(
                select(BookingRecord.id).where(BookingRecord.booking_no == booking_no)
            )
            if not exists.scalar_one_or_none():
                return booking_no
            seq += 1

    async def _lab_to_dict(self, record: LabRecord) -> dict:
        return {
            "lab_code": record.lab_code,
            "name": record.name,
            "capacity": record.capacity,
            "location": record.location,
            "status": record.status,
            "open_hours": record.open_hours,
            "description": record.description,
            "booked_today": await self.count_active_today(record.lab_code),
        }

    async def _booking_to_dict(self, record: BookingRecord) -> dict:
        lab = await self.get_lab(record.lab_code)
        return {
            "booking_no": record.booking_no,
            "student_no": record.student_no,
            "lab_code": record.lab_code,
            "lab_name": lab["name"] if lab else "未知实验室",
            "lab_location": lab["location"] if lab else "未知位置",
            "booking_date": record.booking_date.strftime("%Y-%m-%d"),
            "time_slot": record.time_slot,
            "booking_time": f"{record.booking_date:%Y-%m-%d} {record.time_slot}",
            "status": record.status,
            "purpose": record.purpose,
        }

    def to_lab_object(self, lab: dict) -> dict:
        return {
            "type": "lab",
            "id": lab["lab_code"],
            "title": lab["name"],
            "attributes": {
                "容纳人数": lab["capacity"],
                "位置": lab["location"],
                "预约状态": lab["status"],
                "开放时间": lab["open_hours"],
                "今日已约": lab["booked_today"],
                "简介": lab["description"],
            },
        }

    def to_booking_object(self, booking: dict) -> dict:
        return {
            "type": "booking",
            "id": booking["booking_no"],
            "title": f"{booking['lab_name']} 预约",
            "attributes": {
                "学号": booking["student_no"],
                "实验室编号": booking["lab_code"],
                "实验室": booking["lab_name"],
                "时间": booking["booking_time"],
                "预约状态": booking["status"],
                "用途": booking["purpose"],
            },
        }


async def ensure_schema_and_seed() -> None:
    """启动时保证数据表存在，并在空库时写入示例数据"""
    if database_client.engine is None:
        return

    async with database_client.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with database_client.session_factory() as session:
        lab_exists = (await session.execute(select(func.count(LabRecord.id)))).scalar() or 0
        if not lab_exists:
            session.add_all([LabRecord(**lab) for lab in SEED_LABS])
            await session.commit()

        booking_exists = (await session.execute(select(func.count(BookingRecord.id)))).scalar() or 0
        if not booking_exists:
            session.add_all([
                BookingRecord(
                    booking_no=f"B{datetime.strptime(booking['booking_date'], '%Y-%m-%d'):%Y%m%d}{index:03d}",
                    student_no=booking["student_no"],
                    lab_code=booking["lab_code"],
                    booking_date=datetime.strptime(booking["booking_date"], "%Y-%m-%d").date(),
                    time_slot=booking["time_slot"],
                    status=booking["status"],
                    purpose=booking["purpose"],
                )
                for index, booking in enumerate(SEED_BOOKINGS, start=1)
            ])
            await session.commit()


if __name__ == '__main__':
    import asyncio

    from yoyo.clients.database_client import close_database, init_database

    async def test():
        init_database()
        await ensure_schema_and_seed()
        async with LabBookingRepository.open() as repository:
            labs = await repository.list_labs()
            print(f"实验室数量：{len(labs)}")
            print(random.choice(labs))
            booking = await repository.get_booking("B20261114001")
            print(booking)
        await close_database()

    asyncio.run(test())
