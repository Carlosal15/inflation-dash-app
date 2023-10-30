from pydantic import BaseModel, validator


class Config(BaseModel):
    """
    This class is used for validating the configs provided for getting
    and processing inflation data.  
    """
    url: str
    skiprows: int = 0
    name: str
    date_column: int
    cpi_column: int

    @validator("cpi_column")
    def check_columns(cls, cpi_column, values):
        if cpi_column == values["date_column"]:
            raise ValueError(f"Error loading config {values["name"]}: "
                             "date_column and cpi_column must be different.")
        return cpi_column
