from pydantic import BaseModel


class DailyTip(BaseModel):
    tip: str
