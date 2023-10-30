from pydantic import BaseModel, validator


class Config(BaseModel):
    url: str
    skiprows: int = 0
    freq: str = "Q"
    name: str
    date_column: int
    cpi_column: int

    @validator("cpi_column")
    def check_columns(cls, cpi_column, values):
        if cpi_column == values["date_column"]:
            raise ValueError(f"Error loading config {values["name"]}: "
                             "date_column and cpi_column must be different.")
        return cpi_column
