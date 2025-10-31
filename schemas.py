from pydantic import BaseModel


class DailyTip(BaseModel):
    text: str
