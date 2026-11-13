import importlib
import inspect
import pkgutil

from yoyo.task.action.base import Action
from yoyo.task.action.registry import ActionRegistry


def register_custom_actions(
        registry: ActionRegistry,
) -> None:
    package = importlib.import_module(
        "yoyo.task.action.custom"
    )

    for _, module_name, is_package in pkgutil.iter_modules(
            package.__path__,
            prefix=f"{package.__name__}.",
    ):
        if is_package:
            continue

        module = importlib.import_module(module_name)
        for _, action_class in inspect.getmembers(
                module,
                inspect.isclass,
        ):
            if (
                    not issubclass(action_class, Action)
                    or action_class is Action
            ):
                continue
            if action_class.__module__ != module.__name__:
                continue
            registry.register(action_class())
