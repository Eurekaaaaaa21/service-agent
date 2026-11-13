import re
from datetime import datetime
from typing import Any

from yoyo.domain.state import DialogueState
from yoyo.repository.lab_booking_repository import LabBookingRepository
from yoyo.task.action.base import Action, ActionResult

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_SLOT_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d$")


class CreateBookingAction(Action):
    """为当前用户创建一条实验室预约"""

    name = "action_create_booking"

    async def run(
            self,
            state: DialogueState,
            action_kwargs: dict[str, Any],
    ) -> ActionResult:
        slots = state.task_state.active.slots
        student_no = str(slots.get("student_no") or "").strip()
        lab_code = str(slots.get("lab_code") or "").strip().upper()
        booking_date_text = str(slots.get("booking_date") or "").strip()
        time_slot = str(slots.get("time_slot") or "").strip()
        purpose = str(slots.get("purpose") or "").strip()

        if not student_no:
            return self._fail("缺少学号，请先告诉我你的学号。")
        if not DATE_PATTERN.match(booking_date_text):
            return self._fail("日期格式不对，请按 2026-11-20 这样的格式告诉我预约日期。")
        if not TIME_SLOT_PATTERN.match(time_slot):
            return self._fail("时间段格式不对，请按 14:00-16:00 这样的格式告诉我。")

        try:
            booking_date = datetime.strptime(booking_date_text, "%Y-%m-%d").date()
        except ValueError:
            return self._fail("这个日期不存在，请换一个日期再试。")

        if booking_date < datetime.now().date():
            return self._fail("不能预约已经过去的日期，请换一个日期。")

        async with LabBookingRepository.open() as repository:
            lab = await repository.get_lab(lab_code)
            if lab is None:
                return self._fail(f"没有查询到编号为 {lab_code} 的实验室，请确认后再试。")
            if lab["status"] == "维护中":
                return self._fail(f"{lab['name']}正在维护，暂不开放预约。")
            if lab["status"] == "已满":
                return self._fail(f"{lab['name']}当前已约满，可以换一间实验室。")

            booked = await repository.count_booked(lab["lab_code"], booking_date, time_slot)
            if booked >= lab["capacity"]:
                return self._fail(
                    f"{lab['name']} 在 {booking_date_text} {time_slot} 已经约满"
                    f"（{booked}/{lab['capacity']}），可以换个时间段。"
                )

            booking = await repository.create_booking(
                student_no=student_no,
                lab_code=lab["lab_code"],
                booking_date=booking_date,
                time_slot=time_slot,
                purpose=purpose,
            )

        return ActionResult(slot_updates={
            "booking_ok": True,
            "booking_error": "",
            "booking_no": booking["booking_no"],
            "booking_status": booking["status"],
            "booking_time": booking["booking_time"],
            "booking_lab_name": booking["lab_name"],
            "booking_summary": (
                f"预约号 {booking['booking_no']}，{booking['lab_name']}"
                f"（{booking['lab_code']}，{booking['lab_location']}），"
                f"时间 {booking['booking_time']}，学号 {booking['student_no']}，"
                f"状态 {booking['status']}。"
            ),
        })

    @staticmethod
    def _fail(message: str) -> ActionResult:
        return ActionResult(slot_updates={
            "booking_ok": False,
            "booking_error": message,
        })


class CancelBookingAction(Action):
    """取消一条预约"""

    name = "action_cancel_booking"

    async def run(
            self,
            state: DialogueState,
            action_kwargs: dict[str, Any],
    ) -> ActionResult:
        slots = state.task_state.active.slots
        booking_no = str(slots.get("booking_no") or "").strip().upper()

        async with LabBookingRepository.open() as repository:
            booking = await repository.get_booking(booking_no)
            if booking is None:
                return self._fail(f"没有查询到预约号 {booking_no or '（空）'} 的预约记录。")
            if booking["status"] == "已取消":
                return ActionResult(slot_updates={
                    "cancel_ok": True,
                    "booking_status": booking["status"],
                    "cancel_message": f"预约号 {booking['booking_no']} 之前已经取消过了。",
                })
            if booking["status"] == "已完成":
                return self._fail(f"预约号 {booking['booking_no']} 已经完成，无法取消。")
            if booking["status"] == "使用中":
                return self._fail(f"预约号 {booking['booking_no']} 正在使用中，请联系管理员处理。")

            cancelled = await repository.cancel_booking(booking["booking_no"])

        return ActionResult(slot_updates={
            "cancel_ok": True,
            "booking_status": cancelled["status"],
            "booking_time": cancelled["booking_time"],
            "booking_lab_name": cancelled["lab_name"],
            "cancel_message": (
                f"预约号 {cancelled['booking_no']}（{cancelled['lab_name']}，"
                f"{cancelled['booking_time']}）已取消，现在状态是{cancelled['status']}。"
            ),
        })

    @staticmethod
    def _fail(message: str) -> ActionResult:
        return ActionResult(slot_updates={
            "cancel_ok": False,
            "cancel_message": message,
        })
