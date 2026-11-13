from typing import Any

from yoyo.domain.state import DialogueState
from yoyo.repository.lab_booking_repository import LabBookingRepository
from yoyo.task.action.base import Action, ActionResult


class LookupLabInfoAction(Action):
    """按实验室编号查询实验室基本信息"""

    name = "action_lookup_lab_info"

    async def run(
            self,
            state: DialogueState,
            action_kwargs: dict[str, Any],
    ) -> ActionResult:
        lab_code = (
                state.task_state.active.slots.get("lab_code")
                or action_kwargs.get("lab_code")
        )

        async with LabBookingRepository.open() as repository:
            lab = await repository.get_lab(lab_code or "")

        if lab is None:
            return ActionResult(slot_updates={
                "lab_found": False,
                "lab_code": (lab_code or "").upper(),
                "lab_summary": f"没有查询到编号为 {lab_code or '（空）'} 的实验室，请确认编号后再试。",
            })

        status_hint = {
            "可预约": "现在可以预约",
            "已满": "当前时段名额已满",
            "维护中": "正在维护，暂不开放",
        }.get(lab["status"], lab["status"])

        return ActionResult(slot_updates={
            "lab_found": True,
            "lab_code": lab["lab_code"],
            "lab_name": lab["name"],
            "lab_capacity": lab["capacity"],
            "lab_location": lab["location"],
            "lab_status": lab["status"],
            "lab_open_hours": lab["open_hours"],
            "lab_booked_today": lab["booked_today"],
            "lab_description": lab["description"],
            "lab_summary": (
                f"{lab['name']}（编号 {lab['lab_code']}）位于{lab['location']}，"
                f"可容纳 {lab['capacity']} 人，开放时间 {lab['open_hours']}，"
                f"当前状态：{lab['status']}（{status_hint}），"
                f"今天已预约 {lab['booked_today']} 人。"
                f"{lab['description']}"
            ),
        })
