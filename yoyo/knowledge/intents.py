from dataclasses import dataclass, field


@dataclass
class KnowledgeIntent:
    id: str
    description: str
    provider_ids: list[str] = field(default_factory=list)
    requires_object: str | None = None


KNOWLEDGE_INTENTS: dict[str, KnowledgeIntent] = {
    "lab_info": KnowledgeIntent(
        id="lab_info",
        description="实验室信息咨询，例如某间实验室容纳多少人、在哪个位置、现在能不能预约、开放时间",
        provider_ids=["api.lab"],
        requires_object="lab",
    ),
    "lab_list": KnowledgeIntent(
        id="lab_list",
        description="实验室列表咨询，例如学校有哪些实验室、现在还有哪些实验室可以预约",
        provider_ids=["api.lab.list"],
    ),
    "booking_info": KnowledgeIntent(
        id="booking_info",
        description="预约条信息咨询，例如这条预约约的是哪个实验室、什么时间、当前预约状态",
        provider_ids=["api.booking"],
        requires_object="booking",
    ),
    "booking_rule": KnowledgeIntent(
        id="booking_rule",
        description="预约规则咨询，例如怎么预约、一次能约多久、提前多久能约、怎么取消",
        provider_ids=["faq.default", "rag.default"],
    ),
    "lab_rule": KnowledgeIntent(
        id="lab_rule",
        description="实验室使用规范咨询，例如进实验室要带什么、能不能饮食、设备损坏怎么处理",
        provider_ids=["faq.default", "rag.default"],
    ),
    "open_hours": KnowledgeIntent(
        id="open_hours",
        description="实验室开放时间咨询",
        provider_ids=["faq.default", "rag.default"],
    ),
    "general_lab_info": KnowledgeIntent(
        id="general_lab_info",
        description="实验室预约相关的通用信息咨询，例如预约流程、违约处理、找不到实验室怎么办",
        provider_ids=["faq.default", "rag.default"],
    ),
}
