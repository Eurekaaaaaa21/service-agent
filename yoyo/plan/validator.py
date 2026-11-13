from yoyo.domain.state import DialogueState
from yoyo.knowledge.intents import KnowledgeIntent
from yoyo.plan.models import TurnPlan, TurnPlanValidationResult, ClarifyReason, TaskTurnPlan, KnowledgeTurnPlan
from yoyo.task.command.models import StartFlowCommand, ResumeTaskCommand, CancelTaskCommand, SetSlotsCommand
from yoyo.task.flow.models import FlowCatalog


class TurnPlanValidator:

    def validate(self,
                 turn_plan: TurnPlan,
                 state: DialogueState,
                 flow_catalog: FlowCatalog,
                 knowledge_intents: dict[str, KnowledgeIntent]) -> TurnPlanValidationResult:
        active_tracks: list[str] = []
        if turn_plan.task is not None:
            active_tracks.append('task')

        if turn_plan.knowledge is not None:
            active_tracks.append('knowledge')

        if turn_plan.chitchat is not None:
            active_tracks.append('chitchat')

        if not active_tracks:
            return TurnPlanValidationResult(valid=False, reason=ClarifyReason.MISSING_TRACK)

        if len(active_tracks) > 1:
            return TurnPlanValidationResult(valid=False, reason=ClarifyReason.MULTIPLE_TRACKS)

        active_track = active_tracks[0]

        if active_track == 'task':
            return self._validate_task_plan(turn_plan.task, state, flow_catalog)

        if active_track == 'knowledge':
            return self._validate_knowledge_plan(turn_plan.knowledge, state, knowledge_intents)

        return TurnPlanValidationResult(valid=True)

    def _validate_task_plan(self,
                            task: TaskTurnPlan,
                            state: DialogueState,
                            flow_catalog: FlowCatalog) -> TurnPlanValidationResult:
        if not task.commands:
            return TurnPlanValidationResult(valid=False, reason=ClarifyReason.MISSING_TASK_COMMANDS)

        for command in task.commands:
            if isinstance(command, StartFlowCommand):
                if command.flow not in flow_catalog.flows:
                    return TurnPlanValidationResult(valid=False, reason=ClarifyReason.INVALID_TASK_COMMAND)

            if isinstance(command, ResumeTaskCommand):
                paused_task_ids = [paused_task.task_id for paused_task in state.task_state.paused]
                if command.task_id not in paused_task_ids:
                    return TurnPlanValidationResult(valid=False, reason=ClarifyReason.INVALID_TASK_COMMAND)

            if isinstance(command, CancelTaskCommand):
                all_task_ids = [paused_task.task_id for paused_task in state.task_state.paused]
                if state.task_state.active:
                    all_task_ids.append(state.task_state.active.task_id)

                if command.task_id not in all_task_ids:
                    return TurnPlanValidationResult(valid=False, reason=ClarifyReason.INVALID_TASK_COMMAND)

            if isinstance(command, SetSlotsCommand):
                if not command.slots:
                    return TurnPlanValidationResult(valid=False, reason=ClarifyReason.INVALID_TASK_COMMAND)
                for slot_name in command.slots.keys():
                    if slot_name not in flow_catalog.slots:
                        return TurnPlanValidationResult(valid=False, reason=ClarifyReason.INVALID_TASK_COMMAND)

        return TurnPlanValidationResult(valid=True)

    def _validate_knowledge_plan(self,
                                 knowledge: KnowledgeTurnPlan,
                                 state: DialogueState,
                                 knowledge_intents: dict[str, KnowledgeIntent]) -> TurnPlanValidationResult:

        if not knowledge.intents:
            return TurnPlanValidationResult(valid=False, reason=ClarifyReason.MISSING_KNOWLEDGE_INTENT)

        for intent in knowledge.intents:
            if intent not in knowledge_intents:
                return TurnPlanValidationResult(valid=False, reason=ClarifyReason.UNKNOWN_KNOWLEDGE_INTENT)

            knowledge_intent: KnowledgeIntent = knowledge_intents[intent]
            required_object = knowledge_intent.requires_object
            focused_object = state.shared_state.focused_object

            if required_object and (focused_object is None or required_object != focused_object.type):
                return TurnPlanValidationResult(valid=False, reason=ClarifyReason.MISSING_FOCUSED_OBJECT)

        return TurnPlanValidationResult(valid=True)
