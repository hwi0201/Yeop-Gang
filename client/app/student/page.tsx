"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Trash2, AlertCircle, ArrowLeft, BookOpen, Clock, User, PlayCircle, CheckCircle2, Loader2, XCircle } from "lucide-react";
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
          <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>완료</span>
          </span>
        );
      case "processing":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-yellow-100 px-3 py-1 text-xs font-medium text-yellow-700">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span>처리 중</span>
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-700">
            <XCircle className="h-3.5 w-3.5" />
            <span>실패</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
            <span>{status}</span>
          </span>
        );
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="mx-auto max-w-6xl px-6 py-10">
        {/* 네비게이션 */}
        <div className="mb-8">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-slate-600 transition-colors hover:text-slate-900"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>홈으로</span>
          </Link>
        </div>

        {/* 헤더 */}
        <header className="mb-8">
          <div className="mb-3 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
              <BookOpen className="h-5 w-5" />
            </div>
        <div>
              <h1 className="text-3xl font-bold text-slate-900">강의 목록</h1>
              <p className="mt-1 text-sm text-slate-500">
            수강할 강의를 선택하세요
          </p>
        </div>
          </div>
          <div className="mt-4">
        <Link
          href="/instructor/upload"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-blue-500 hover:bg-blue-50"
        >
              <span>새 강의 업로드</span>
        </Link>
          </div>
      </header>

      {isLoading && (
        <div className="flex flex-col items-center justify-center gap-4 py-16">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <span className="text-sm text-slate-600">강의 목록을 불러오는 중...</span>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6">
          <div className="mb-4 flex items-start gap-3">
            <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-600" />
            <div className="flex-1">
              <h3 className="mb-1 text-sm font-semibold text-red-900">오류 발생</h3>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
          <button
            onClick={fetchCourses}
            className="w-full rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
          >
            다시 시도
          </button>
        </div>
      )}

      {!isLoading && !error && (
        <>
          {courses.length === 0 ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-sm">
              <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                <BookOpen className="h-8 w-8" />
              </div>
              <h3 className="mb-2 text-lg font-semibold text-slate-900">등록된 강의가 없습니다</h3>
              <p className="mb-6 text-sm text-slate-600">새로운 강의를 업로드하여 시작하세요</p>
              <Link
                href="/instructor/upload"
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
              >
                <span>강의 업로드하기</span>
              </Link>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {courses.map((course) => (
                <div
                  key={course.id}
                  className={`group relative rounded-2xl border bg-white p-6 shadow-sm transition-all hover:shadow-lg ${
                    course.status === "completed"
                      ? "border-slate-200 hover:border-blue-300"
                      : course.status === "processing"
                      ? "border-yellow-200 bg-yellow-50/50"
                      : "border-red-200 bg-red-50/50"
                  }`}
                >
                  {/* 삭제 버튼 */}
                  <button
                    onClick={(e) => handleDelete(course.id, e)}
                    disabled={deletingCourseId === course.id}
                    className="absolute top-4 right-4 rounded-lg bg-red-100 p-2 text-red-600 transition-colors hover:bg-red-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    title="강의 삭제"
                  >
                    {deletingCourseId === course.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
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
                    {/* 상태 배지 */}
                    <div className="mb-4 flex items-center justify-between">
                      {getStatusBadge(course.status)}
                    </div>

                    {/* 강의 제목 */}
                    <h3 className="mb-3 text-lg font-semibold text-slate-900 transition-colors group-hover:text-blue-600 line-clamp-2 pr-8">
                      {course.title || course.id}
                    </h3>

                    {/* 강의 정보 */}
                    <div className="space-y-2.5 border-t border-slate-100 pt-4">
                      {course.created_at && (
                        <div className="flex items-center gap-2 text-sm text-slate-600">
                          <Clock className="h-4 w-4 text-slate-400" />
                          <span>{new Date(course.created_at).toLocaleDateString("ko-KR")}</span>
                      </div>
                    )}
                      {course.status === "processing" && (
                        <div className="flex items-center gap-2 text-sm text-yellow-700">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span>진행률: {course.progress}%</span>
                      </div>
                    )}
                  </div>

                    {/* 액션 버튼 */}
                  {course.status === "completed" && (
                      <div className="mt-4 flex items-center justify-between rounded-lg bg-blue-50 px-4 py-2.5 text-sm font-medium text-blue-700 transition-colors group-hover:bg-blue-100">
                        <span>수강하기</span>
                        <PlayCircle className="h-4 w-4" />
                    </div>
                  )}

                  {course.status === "processing" && (
                      <div className="mt-4 rounded-lg bg-yellow-50 px-4 py-2.5 text-sm text-yellow-700">
                        <div className="flex items-center gap-2">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span>처리 중입니다</span>
                      </div>
                    </div>
                  )}

                  {course.status === "failed" && (
                      <div className="mt-4 rounded-lg bg-red-50 px-4 py-2.5 text-sm text-red-700">
                        <div className="flex items-center gap-2">
                          <XCircle className="h-4 w-4" />
                          <span>처리 실패</span>
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
      </div>
    </main>
  );
}

