import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

from yoyo.domain.message import UserMessage
from yoyo.domain.state import DialogueState
from yoyo.repository.lab_booking_repository import LabBookingRepository


@dataclass
class KnowledgeChunk:
    content: str = ""


class KnowledgeProvider(ABC):
    provider_id: str = ""

    @abstractmethod
    async def retrieve(self, user_message: UserMessage, state: DialogueState) -> list[KnowledgeChunk]:
        pass


class APILabProvider(KnowledgeProvider):
    """按聚焦的实验室编号查询实验室详情"""

    provider_id: str = "api.lab"

    async def retrieve(self, user_message: UserMessage, state: DialogueState) -> list[KnowledgeChunk]:
        focused_object = state.shared_state.focused_object
        if focused_object is None:
            return [KnowledgeChunk(content="未获取到实验室编号")]

        async with LabBookingRepository.open() as repository:
            lab = await repository.get_lab(focused_object.id)

        if lab is None:
            return [KnowledgeChunk(content=f"没有查询到编号为 {focused_object.id} 的实验室")]

        return [KnowledgeChunk(content=json.dumps(lab, ensure_ascii=False, indent=2))]


class APILabListProvider(KnowledgeProvider):
    """查询实验室清单"""

    provider_id: str = "api.lab.list"

    async def retrieve(self, user_message: UserMessage, state: DialogueState) -> list[KnowledgeChunk]:
        async with LabBookingRepository.open() as repository:
            labs = await repository.list_labs()

        if not labs:
            return [KnowledgeChunk(content="暂未维护实验室信息")]

        brief = [
            {
                "实验室编号": lab["lab_code"],
                "名称": lab["name"],
                "容纳人数": lab["capacity"],
                "位置": lab["location"],
                "预约状态": lab["status"],
                "开放时间": lab["open_hours"],
            }
            for lab in labs
        ]
        return [KnowledgeChunk(content=json.dumps(brief, ensure_ascii=False, indent=2))]


class APIBookingProvider(KnowledgeProvider):
    """按聚焦的预约号查询预约详情"""

    provider_id: str = "api.booking"

    async def retrieve(self, user_message: UserMessage, state: DialogueState) -> list[KnowledgeChunk]:
        focused_object = state.shared_state.focused_object
        if focused_object is None:
            return [KnowledgeChunk(content="未获取到预约号")]

        async with LabBookingRepository.open() as repository:
            booking = await repository.get_booking(focused_object.id)

        if booking is None:
            return [KnowledgeChunk(content=f"没有查询到预约号为 {focused_object.id} 的预约记录")]

        return [KnowledgeChunk(content=json.dumps(booking, ensure_ascii=False, indent=2))]


class FAQProvider(KnowledgeProvider):
    provider_id = "faq.default"

    # 固定的预约与实验室使用说明，作为常见问题的知识来源
    FAQ_CONTENT = {
        "booking_rule": (
            "【预约规则】\n"
            "1. 至少提前 1 天预约，单次预约时长 2 小时，每天最多预约 2 个时段。\n"
            "2. 预约成功后可在开始前 2 小时内取消，超过时间未到馆会记为一次违约。\n"
            "3. 一学期累计 3 次违约，将暂停预约权限 30 天。\n"
            "4. 预约时请填写真实学号，入馆需要刷校园卡核对身份。"
        ),
        "lab_rule": (
            "【实验室使用规范】\n"
            "1. 凭学生证或校园卡进入，不得转借他人使用预约名额。\n"
            "2. 实验室内禁止饮食，离开前请关闭设备电源并整理工位。\n"
            "3. 设备出现故障请立即告知管理员，不得自行拆装。\n"
            "4. 人为损坏设备需按学校规定赔偿。"
        ),
        "open_hours": (
            "【开放时间】\n"
            "大部分实验室工作日 08:00-22:00 开放，周末 09:00-21:00。\n"
            "具体开放时间以各实验室详情为准，处于「维护中」的实验室暂不开放。"
        ),
        "general_lab_info": (
            "【预约流程】\n"
            "1. 说出想约的实验室编号或直接说「帮我预约实验室」，我会帮你登记学号、实验室、日期和时间段。\n"
            "2. 提交后会生成 12 位预约号，凭预约号可以查状态或取消。\n"
            "3. 到馆后出示预约号，管理员确认后状态变为「使用中」，使用结束变为「已完成」。\n"
            "实验室状态分为：可预约、已满、维护中。"
        ),
    }

    async def retrieve(self, user_message: UserMessage, state: DialogueState) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(content="\n\n".join(self.FAQ_CONTENT.values()))]


class RAGProvider(KnowledgeProvider):
    provider_id = "rag.default"

    async def retrieve(self, user_message: UserMessage, state: DialogueState) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(content="未检索到相关资料")]
