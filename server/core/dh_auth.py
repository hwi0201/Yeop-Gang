"""
인증/인가 시스템
- JWT 기반 인증
- 역할 기반 접근 제어 (RBAC)
- 멀티 테넌트 데이터 격리
"""
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from core.db import get_session
from core.dh_models import Student
from core.models import Instructor, UserRole

# JWT 설정
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer 토큰
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """JWT 토큰 디코딩"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> dict:
    """현재 사용자 정보 가져오기"""
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: str = payload.get("sub")
    user_role: str = payload.get("role")
    
    if not user_id or not user_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    # 사용자 정보 확인
    if user_role == UserRole.instructor:
        instructor = session.get(Instructor, user_id)
        if not instructor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instructor not found",
            )
        return {
            "id": instructor.id,
            "role": UserRole.instructor,
            "name": instructor.name,
            "email": instructor.email,
        }
    elif user_role == UserRole.student:
        student = session.get(Student, user_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found",
            )
        return {
            "id": student.id,
            "role": UserRole.student,
            "name": student.name,
            "email": student.email,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user role",
        )


def require_role(allowed_roles: list[UserRole]):
    """역할 기반 접근 제어 데코레이터"""
    def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}",
            )
        return current_user
    return role_checker


def require_instructor():
    """강사만 접근 가능"""
    return require_role([UserRole.instructor])


def require_student():
    """학생만 접근 가능"""
    return require_role([UserRole.student])


def require_any_user():
    """강사 또는 학생 접근 가능"""
    return require_role([UserRole.instructor, UserRole.student])


async def verify_course_access(
    course_id: str,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """강의 접근 권한 확인 (멀티 테넌트 데이터 격리)"""
    from core.models import Course
    from core.dh_models import CourseEnrollment
    
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    
    user_role = current_user["role"]
    user_id = current_user["id"]
    
    # 강사는 자신의 강의만 접근 가능
    if user_role == UserRole.instructor:
        if course.instructor_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. This course belongs to another instructor.",
            )
    
    # 학생은 등록한 강의만 접근 가능
    elif user_role == UserRole.student:
        enrollment = session.exec(
            select(CourseEnrollment).where(
                CourseEnrollment.student_id == user_id,
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.status == "active"
            )
        ).first()
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You are not enrolled in this course.",
            )
    
    return current_user

