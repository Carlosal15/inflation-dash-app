from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        str(self)


class ConfigFields(StrEnum):
    URL = "url"
    SKIPROWS = "skiprows"
    FREQ = "freq"
    NAME = "name"
    DATE_COLUMN = "date_column"
    CPI_COLUMN = "cpi_column"
