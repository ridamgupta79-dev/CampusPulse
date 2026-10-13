
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_code: str
    full_name: str
    program: str
    department: str
    year_of_study: int
    cohort: str
    advisor_name: str | None
    mentor_name: str | None
    created_at: datetime
