from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from yoyo.models.base import Base


class LabRecord(Base):
    """实验室：名称、容纳人数、位置、预约状态"""

    __tablename__ = "labs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lab_code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        unique=True,
        comment="实验室编号，对用户展示的唯一标识",
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="实验室名称")
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, comment="容纳人数")
    location: Mapped[str] = mapped_column(String(128), nullable=False, comment="实验室位置")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="可预约",
        comment="预约状态：可预约/已满/维护中",
    )
    open_hours: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="08:00-22:00",
        comment="开放时间",
    )
    description: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        default="",
        comment="实验室用途与设备简介",
    )


class BookingRecord(Base):
    """预约条：学号、时间、实验室编号、预约状态"""

    __tablename__ = "bookings"
    __table_args__ = (UniqueConstraint("booking_no", name="uk_booking_no"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    booking_no: Mapped[str] = mapped_column(String(32), nullable=False, comment="预约号")
    student_no: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="学号")
    lab_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="实验室编号")
    booking_date: Mapped[date] = mapped_column(Date, nullable=False, comment="预约日期")
    time_slot: Mapped[str] = mapped_column(String(32), nullable=False, comment="时间段，例如 14:00-16:00")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="待到馆",
        comment="预约状态：待到馆/使用中/已完成/已取消",
    )
    purpose: Mapped[str] = mapped_column(String(255), nullable=False, default="", comment="使用用途")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )
