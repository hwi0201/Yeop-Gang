"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  BookOpen,
  Clock,
  Upload,
  CheckCircle2,
  Loader2,
  XCircle,
  AlertCircle,
  List,
  Plus,
  X,
  Trash2,
} from "lucide-react";
import { apiGet, apiDelete, handleApiError } from "../../../../../lib/api";
import UploadForm from "../../../../../components/UploadForm";

type Chapter = {
  id: string;
  title: string;
  chapter_number?: number;
  status: string;
  progress: number;
  created_at?: string;
};

type CourseInfo = {
  id: string;
  title: string;
  category?: string;
  instructor_id: string;
  instructor_name?: string;
  total_chapters?: number;
};

type ChaptersResponse = {
  course: CourseInfo;
  chapters: Chapter[];
};

export default function InstructorChaptersPage() {
  const params = useParams();
  const router = useRouter();
  const courseId = params.course_id as string;
  
  const [courseInfo, setCourseInfo] = useState<CourseInfo | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [instructorId, setInstructorId] = useState<string | null>(null);
  const [showUploadForm, setShowUploadForm] = useState(false);

  useEffect(() => {
    // 로그인 확인
    if (typeof window !== "undefined") {
      const id = localStorage.getItem("instructor_id");
      const token = localStorage.getItem("instructor_token");
      
      if (!id || !token) {
        router.push("/instructor/login");
        return;
      }
      
      setInstructorId(id);
      if (courseId) {
        fetchChapters();
      }
    }
  }, [courseId, router]);

  const fetchChapters = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await apiGet<ChaptersResponse>(`/api/courses/${courseId}/chapters`);
      setCourseInfo(data.course);
      setChapters(data.chapters);
    } catch (err) {
      console.error("챕터 목록 조회 오류:", err);
      const apiError = handleApiError(err);
      setError(apiError.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteChapter = async (chapterId: string) => {
    if (!confirm(`챕터를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) {
      return;
    }

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("instructor_token") : null;
      if (!token) {
        throw new Error("로그인이 필요합니다.");
      }

      await apiDelete(`/api/instructor/courses/${chapterId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      // 목록에서 제거
      setChapters((prev) => prev.filter((c) => c.id !== chapterId));
    } catch (err) {
      console.error("챕터 삭제 오류:", err);
      const apiError = handleApiError(err);
      alert(`챕터 삭제 실패: ${apiError.message}`);
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

  const handleUploadSuccess = () => {
    setShowUploadForm(false);
    fetchChapters();
  };

  if (!instructorId) {
    return null; // 로그인 체크 중
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="mx-auto max-w-6xl px-6 py-10">
        {/* 네비게이션 */}
        <div className="mb-8">
          <Link
            href="/instructor/courses"
            className="inline-flex items-center gap-2 text-sm text-slate-600 transition-colors hover:text-slate-900"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>강의 목록으로</span>
          </Link>
        </div>

        {/* 헤더 */}
        <header className="mb-8">
          <div className="mb-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
                <List className="h-5 w-5" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-slate-900">
                  {courseInfo?.title || "챕터 관리"}
                </h1>
                <p className="mt-1 text-sm text-slate-500">
                  {chapters.length > 0 
                    ? `${chapters.length}개 챕터` 
                    : "챕터를 추가하세요"}
                </p>
                {courseInfo?.category && (
                  <p className="mt-0.5 text-xs text-slate-400">
                    카테고리: {courseInfo.category}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowUploadForm(!showUploadForm)}
                className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors ${
                  showUploadForm
                    ? "bg-red-600 hover:bg-red-700"
                    : "bg-blue-600 hover:bg-blue-700"
                }`}
              >
                {showUploadForm ? (
                  <X className="h-4 w-4" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                <span>{showUploadForm ? "업로드 폼 닫기" : "챕터 추가"}</span>
              </button>
            </div>
          </div>
        </header>

        {/* 챕터 업로드 폼 */}
        {showUploadForm && instructorId && (
          <div className="mb-8">
            <UploadForm
              instructorId={instructorId}
              parentCourseId={courseId}
              totalChapters={courseInfo?.total_chapters}
              onSubmitted={handleUploadSuccess}
            />
          </div>
        )}

        {isLoading && (
          <div className="flex flex-col items-center justify-center gap-4 py-16">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <span className="text-sm text-slate-600">챕터 목록을 불러오는 중...</span>
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
              onClick={fetchChapters}
              className="w-full rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
            >
              다시 시도
            </button>
          </div>
        )}

        {!isLoading && !error && (
          <>
            {chapters.length === 0 ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-sm">
                <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                  <BookOpen className="h-8 w-8" />
                </div>
                <h3 className="mb-2 text-lg font-semibold text-slate-900">
                  등록된 챕터가 없습니다
                </h3>
                <p className="mb-6 text-sm text-slate-600">
                  "챕터 추가" 버튼을 눌러 첫 번째 챕터를 업로드하세요
                </p>
                <button
                  onClick={() => setShowUploadForm(true)}
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
                >
                  <Plus className="h-4 w-4" />
                  <span>챕터 추가하기</span>
                </button>
              </div>
            ) : (
              <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
                {/* 테이블 헤더 */}
                <div className="grid grid-cols-12 gap-4 px-6 py-3 bg-slate-50 border-b border-slate-200 text-sm font-semibold text-slate-700">
                  <div className="col-span-1">번호</div>
                  <div className="col-span-4">챕터명</div>
                  <div className="col-span-2">상태</div>
                  <div className="col-span-2">생성일</div>
                  <div className="col-span-2">진행률</div>
                  <div className="col-span-1 text-center">작업</div>
                </div>

                {/* 챕터 리스트 */}
                <div className="divide-y divide-slate-100">
                  {chapters.map((chapter, index) => {
                    const RowContent = (
                      <>
                        {/* 번호 */}
                        <div className="col-span-1">
                          <span className="text-sm font-medium text-slate-600">
                            {chapter.chapter_number || index + 1}
                          </span>
                        </div>

                        {/* 챕터명 */}
                        <div className="col-span-4">
                          <h3 className="text-sm font-semibold text-slate-900 group-hover:text-blue-600 transition-colors">
                            {chapter.title || chapter.id}
                          </h3>
                          {chapter.id && (
                            <p className="text-xs text-slate-400 mt-0.5 truncate">
                              {chapter.id}
                            </p>
                          )}
                        </div>

                        {/* 상태 */}
                        <div className="col-span-2">
                          {getStatusBadge(chapter.status)}
                        </div>

                        {/* 생성일 */}
                        <div className="col-span-2">
                          {chapter.created_at ? (
                            <div className="flex items-center gap-1.5 text-sm text-slate-600">
                              <Clock className="h-3.5 w-3.5 text-slate-400" />
                              <span>{new Date(chapter.created_at).toLocaleDateString("ko-KR")}</span>
                            </div>
                          ) : (
                            <span className="text-sm text-slate-400">-</span>
                          )}
                        </div>

                        {/* 진행률 */}
                        <div className="col-span-2">
                          {chapter.status === "processing" ? (
                            <div className="flex items-center gap-2">
                              <Loader2 className="h-3.5 w-3.5 animate-spin text-yellow-600" />
                              <span className="text-sm text-yellow-700">{chapter.progress}%</span>
                            </div>
                          ) : chapter.status === "completed" ? (
                            <span className="text-sm text-green-600">100%</span>
                          ) : (
                            <span className="text-sm text-slate-400">-</span>
                          )}
                        </div>

                        {/* 작업 버튼 - 삭제만 */}
                        <div 
                          className="col-span-1 flex items-center justify-center"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              handleDeleteChapter(chapter.id);
                            }}
                            className="rounded-lg bg-red-50 p-2 text-red-600 transition-colors hover:bg-red-100"
                            title="챕터 삭제"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </>
                    );

                    // 완료된 챕터는 행 전체가 클릭 가능
                    if (chapter.status === "completed") {
                      return (
                        <Link
                          key={chapter.id}
                          href={`/student/play/${chapter.id}`}
                          className={`group grid grid-cols-12 gap-4 px-6 py-4 items-center transition-colors hover:bg-blue-50/50 cursor-pointer`}
                        >
                          {RowContent}
                        </Link>
                      );
                    }

                    // 처리 중이거나 실패한 챕터는 클릭 불가
                    return (
                      <div
                        key={chapter.id}
                        className={`group grid grid-cols-12 gap-4 px-6 py-4 items-center transition-colors ${
                          chapter.status === "processing"
                            ? "bg-yellow-50/30 hover:bg-yellow-50/50"
                            : "bg-red-50/30 hover:bg-red-50/50"
                        }`}
                      >
                        {RowContent}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}

