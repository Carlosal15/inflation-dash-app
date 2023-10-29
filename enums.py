from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        str(self)


class ConfigFields(StrEnum):
    URL = "url"
    SKIPROWS = "skiprows"
    USECOLS = "usecols"
    FREQ = "freq"
    NAME = "name"
