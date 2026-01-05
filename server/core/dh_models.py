"""
멀티 테넌트 DB 모델 확장
- Student 모델 추가
- 강의 등록 관리
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class EnrollmentStatus(str, Enum):
    """강의 등록 상태"""
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


class Student(SQLModel, table=True):
    """학생 모델 - 멀티 테넌트 데이터 격리를 위한 모델"""
    id: str = Field(primary_key=True, index=True)
    name: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 학생이 등록한 강의들
    enrollments: list["CourseEnrollment"] = Relationship(back_populates="student")


class CourseEnrollment(SQLModel, table=True):
    """강의 등록 정보 - 학생과 강의 간의 관계 (멀티 테넌트 데이터 격리)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: str = Field(foreign_key="student.id", index=True)
    course_id: str = Field(foreign_key="course.id", index=True)
    status: EnrollmentStatus = Field(default=EnrollmentStatus.active)
    enrolled_at: datetime = Field(default_factory=datetime.utcnow)
    
    student: Student = Relationship(back_populates="enrollments")

