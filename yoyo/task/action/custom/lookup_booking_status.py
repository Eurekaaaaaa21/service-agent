from typing import Any

from yoyo.domain.state import DialogueState
from yoyo.repository.lab_booking_repository import LabBookingRepository
from yoyo.task.action.base import Action, ActionResult


class LookupBookingStatusAction(Action):
    """按预约号查询预约条状态"""

    name = "action_lookup_booking_status"

    async def run(
            self,
            state: DialogueState,
            action_kwargs: dict[str, Any],
    ) -> ActionResult:
        booking_no = (
                state.task_state.active.slots.get("booking_no")
                or action_kwargs.get("booking_no")
        )

        async with LabBookingRepository.open() as repository:
            booking = await repository.get_booking(booking_no or "")

        if booking is None:
            return ActionResult(slot_updates={
                "booking_found": False,
                "booking_status": "未找到",
                "booking_summary": f"没有查询到预约号 {booking_no or '（空）'} 的预约记录，请核对预约号后再试。",
            })

        return ActionResult(slot_updates={
            "booking_found": True,
            "booking_no": booking["booking_no"],
            "booking_status": booking["status"],
            "booking_lab_name": booking["lab_name"],
            "booking_time": booking["booking_time"],
            "student_no": booking["student_no"],
            "booking_purpose": booking["purpose"] or "未填写",
            "booking_summary": (
                f"预约号 {booking['booking_no']}：{booking['lab_name']}"
                f"（{booking['lab_code']}，{booking['lab_location']}），"
                f"时间 {booking['booking_time']}，学号 {booking['student_no']}，"
                f"用途 {booking['purpose'] or '未填写'}。"
            ),
        })
