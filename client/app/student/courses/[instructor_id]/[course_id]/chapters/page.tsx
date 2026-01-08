"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  BookOpen,
  PlayCircle,
  Loader2,
  AlertCircle,
  List,
} from "lucide-react";
import { apiGet, handleApiError } from "../../../../../../lib/api";

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
};

type ChaptersResponse = {
  course: CourseInfo;
  chapters: Chapter[];
};

export default function CourseChaptersPage() {
  const params = useParams();
  const instructorId = params.instructor_id as string;
  const courseId = params.course_id as string;
  
  const [courseInfo, setCourseInfo] = useState<CourseInfo | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (courseId) {
      fetchChapters();
    }
  }, [courseId]);

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


  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="mx-auto max-w-6xl px-6 py-10">
        {/* 네비게이션 */}
        <div className="mb-8">
          <Link
            href={`/student/courses/${instructorId}`}
            className="inline-flex items-center gap-2 text-sm text-slate-600 transition-colors hover:text-slate-900"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>강의 목록으로</span>
          </Link>
        </div>

        {/* 헤더 */}
        <header className="mb-8">
          <div className="mb-3 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
              <List className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-slate-900">
                {courseInfo?.title || "챕터 목록"}
              </h1>
              <p className="mt-1 text-sm text-slate-500">
                {chapters.filter((c) => c.status === "completed").length > 0
                  ? `수강 가능한 챕터 ${chapters.filter((c) => c.status === "completed").length}개`
                  : "수강 가능한 챕터가 없습니다"}
              </p>
              {courseInfo?.category && (
                <p className="mt-0.5 text-xs text-slate-400">
                  카테고리: {courseInfo.category}
                </p>
              )}
            </div>
          </div>
        </header>

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
            {chapters.filter((c) => c.status === "completed").length === 0 ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-sm">
                <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                  <BookOpen className="h-8 w-8" />
                </div>
                <h3 className="mb-2 text-lg font-semibold text-slate-900">
                  수강 가능한 챕터가 없습니다
                </h3>
                <p className="text-sm text-slate-600">
                  챕터가 아직 준비 중이거나 업로드되지 않았습니다
                </p>
              </div>
            ) : (
              <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
                {/* 테이블 헤더 */}
                <div className="grid grid-cols-12 gap-4 px-6 py-3 bg-slate-50 border-b border-slate-200 text-sm font-semibold text-slate-700">
                  <div className="col-span-1">번호</div>
                  <div className="col-span-9">챕터명</div>
                  <div className="col-span-2 text-center">작업</div>
                </div>

                {/* 챕터 리스트 */}
                <div className="divide-y divide-slate-100">
                  {chapters
                    .filter((chapter) => chapter.status === "completed")
                    .map((chapter, index) => {
                      const chapterNum = chapter.chapter_number || index + 1;
                      return (
                        <Link
                          key={chapter.id}
                          href={`/student/play/${chapter.id}`}
                          className="group grid grid-cols-12 gap-4 px-6 py-4 items-center transition-colors hover:bg-blue-50/50 cursor-pointer"
                        >
                          {/* 번호 */}
                          <div className="col-span-1">
                            <span className="text-sm font-medium text-slate-600">
                              {chapterNum}
                            </span>
                          </div>

                          {/* 챕터명 */}
                          <div className="col-span-9">
                            <h3 className="text-sm font-semibold text-slate-900 group-hover:text-blue-600 transition-colors">
                              {chapter.title || chapter.id}
                            </h3>
                          </div>

                          {/* 수강하기 버튼 */}
                          <div className="col-span-2 flex justify-center">
                            <div className="inline-flex items-center gap-1.5 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 transition-colors group-hover:bg-blue-100">
                              <PlayCircle className="h-3.5 w-3.5" />
                              <span>수강하기</span>
                            </div>
                          </div>
                        </Link>
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

