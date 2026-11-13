from dataclasses import dataclass
from enum import Enum

from pydantic import TypeAdapter


class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3


@dataclass
class Data:
    a: int
    b: float
    c: Color


data = Data(a=1, b=2.0, c=Color.RED)

adapter = TypeAdapter(Data)
print(adapter.dump_json(data).decode("utf-8"))
