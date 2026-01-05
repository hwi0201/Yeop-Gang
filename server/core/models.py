from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class CourseStatus(str, Enum):
    processing = "processing"
    completed = "completed"
    failed = "failed"


class UserRole(str, Enum):
    instructor = "instructor"
    student = "student"


class Instructor(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    name: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    courses: list["Course"] = Relationship(back_populates="instructor")


class Course(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    instructor_id: str = Field(foreign_key="instructor.id")
    title: Optional[str] = None
    status: CourseStatus = Field(default=CourseStatus.processing)
    progress: int = Field(default=0, description="처리 진행도 (0-100)")  # 0-100%
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    instructor: Instructor = Relationship(back_populates="courses")
    videos: list["Video"] = Relationship(back_populates="course")
    sessions: list["ChatSession"] = Relationship(back_populates="course")


class Video(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: str = Field(foreign_key="course.id")
    filename: str
    filetype: str = Field(default="video")  # video | pdf
    storage_path: str
    transcript_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    course: Course = Relationship(back_populates="videos")


class ChatSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: str = Field(foreign_key="course.id")
    user_role: UserRole = Field(default=UserRole.student)
    status: CourseStatus = Field(default=CourseStatus.completed)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    course: Course = Relationship(back_populates="sessions")


# dh: Student 모델은 server/core/dh_models.py에 정의됨
