"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Trash2, AlertCircle } from "lucide-react";
import { apiGet, apiDelete, handleApiError } from "../../lib/api";

type Course = {
  id: string;
  title: string;
  status: string;
  instructor_id: string;
  created_at?: string;
  progress: number;
};

export default function StudentPage() {
  const router = useRouter();
  const [courses, setCourses] = useState<Course[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingCourseId, setDeletingCourseId] = useState<string | null>(null);

  useEffect(() => {
    fetchCourses();
  }, []);

  const fetchCourses = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await apiGet<Course[]>("/api/courses");
      setCourses(data);
    } catch (err) {
      console.error("강의 목록 조회 오류:", err);
      const apiError = handleApiError(err);
      setError(apiError.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (courseId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!confirm(`강의 '${courseId}'를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) {
      return;
    }
    
    setDeletingCourseId(courseId);
    
    try {
      await apiDelete(`/api/courses/${courseId}`);
      
      // 목록에서 제거
      setCourses((prev) => prev.filter((c) => c.id !== courseId));
    } catch (err) {
      console.error("강의 삭제 오류:", err);
      const apiError = handleApiError(err);
      alert(`강의 삭제 실패: ${apiError.message}`);
    } finally {
      setDeletingCourseId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return (
          <span className="rounded-full bg-green-50 px-2 py-0.5 text-xs text-green-700 border border-green-200">
            완료
          </span>
        );
      case "processing":
        return (
          <span className="rounded-full bg-yellow-50 px-2 py-0.5 text-xs text-yellow-700 border border-yellow-200">
            처리 중
          </span>
        );
      case "failed":
        return (
          <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-700 border border-red-200">
            실패
          </span>
        );
      default:
        return (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 border border-slate-200">
            {status}
          </span>
        );
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 px-6 py-10 bg-white">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">
            Student
          </p>
          <h1 className="text-2xl font-bold text-slate-900">강의 목록</h1>
          <p className="text-sm text-slate-600 mt-1">
            수강할 강의를 선택하세요
          </p>
        </div>
        <Link
          href="/instructor/upload"
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
        >
          강사용 업로드
        </Link>
      </header>

      {isLoading && (
        <div className="flex items-center justify-center gap-3 py-12">
          <div className="flex gap-1">
            <div className="h-2 w-2 animate-bounce rounded-full bg-blue-500 [animation-delay:-0.3s]"></div>
            <div className="h-2 w-2 animate-bounce rounded-full bg-blue-500 [animation-delay:-0.15s]"></div>
            <div className="h-2 w-2 animate-bounce rounded-full bg-blue-500"></div>
          </div>
          <span className="text-sm text-slate-500">강의 목록 불러오는 중...</span>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <div className="mb-2 flex items-center gap-2 text-sm text-red-700">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
          <button
            onClick={fetchCourses}
            className="w-full rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 transition-colors"
          >
            다시 시도
          </button>
        </div>
      )}

      {!isLoading && !error && (
        <>
          {courses.length === 0 ? (
            <div className="rounded-xl border border-slate-200 bg-white shadow-sm p-8 text-center">
              <p className="text-slate-600 mb-4">등록된 강의가 없습니다.</p>
              <Link
                href="/instructor/upload"
                className="inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
              >
                강의 업로드하러 가기
              </Link>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {courses.map((course) => (
                <div
                  key={course.id}
                  className={`group rounded-xl border p-4 transition-all hover:border-blue-500 hover:shadow-md relative ${
                    course.status === "completed"
                      ? "border-slate-200 bg-white"
                      : course.status === "processing"
                      ? "border-yellow-200 bg-yellow-50"
                      : "border-slate-200 bg-slate-50"
                  }`}
                >
                  {/* 삭제 버튼 */}
                  <button
                    onClick={(e) => handleDelete(course.id, e)}
                    disabled={deletingCourseId === course.id}
                    className="absolute top-3 right-3 rounded-md bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors z-10"
                    title="강의 삭제"
                  >
                    {deletingCourseId === course.id ? (
                      "삭제 중..."
                    ) : (
                      <Trash2 className="w-3 h-3" />
                    )}
                  </button>
                  
                  <Link
                    href={`/student/play/${course.id}`}
                    className={`block ${
                      course.status === "completed"
                        ? "cursor-pointer"
                        : course.status === "processing"
                        ? "cursor-pointer"
                        : "cursor-not-allowed"
                    }`}
                  >
                    <div className="mb-3 flex items-start justify-between pr-8">
                      <div className="flex-1">
                        <h3 className="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors">
                          {course.title}
                        </h3>
                        <p className="text-xs text-slate-500 mt-1">
                          ID: {course.id}
                        </p>
                      </div>
                      {getStatusBadge(course.status)}
                    </div>

                  <div className="space-y-2 text-xs text-slate-600">
                    <div className="flex items-center justify-between">
                      <span>강사 ID</span>
                      <span className="text-slate-700">{course.instructor_id}</span>
                    </div>
                    {course.status === "processing" && (
                      <div className="flex items-center justify-between">
                        <span>진행률</span>
                        <span className="text-yellow-600">{course.progress}%</span>
                      </div>
                    )}
                    {course.created_at && (
                      <div className="flex items-center justify-between">
                        <span>생성일</span>
                        <span className="text-slate-700">
                          {new Date(course.created_at).toLocaleDateString("ko-KR")}
                        </span>
                      </div>
                    )}
                  </div>

                  {course.status === "completed" && (
                    <div className="mt-3 pt-3 border-t border-slate-200">
                      <div className="text-xs text-blue-600 font-medium">
                        클릭하여 수강하기 →
                      </div>
                    </div>
                  )}

                  {course.status === "processing" && (
                    <div className="mt-3 pt-3 border-t border-slate-200">
                      <div className="text-xs text-yellow-600 font-medium">
                        처리 중... 잠시 후 다시 시도하세요
                      </div>
                    </div>
                  )}

                  {course.status === "failed" && (
                    <div className="mt-3 pt-3 border-t border-slate-200">
                      <div className="text-xs text-red-600 font-medium">
                        처리 실패
                      </div>
                    </div>
                  )}
                  </Link>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </main>
  );
}

