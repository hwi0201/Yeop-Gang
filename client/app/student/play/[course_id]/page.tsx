"use client";

import { useRef, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Play, FileText, PenTool, ArrowLeft } from "lucide-react";
import ChatPanel from "../../../../components/ChatPanel";
import SummaryNote from "../../../../components/SummaryNote";
import Quiz from "../../../../components/Quiz";
import VideoPlayer, { VideoPlayerRef } from "../../../../components/VideoPlayer";
import { apiGet } from "../../../../lib/api";

type Props = {
  params: { course_id: string };
};

type ContentType = "video" | "summary" | "quiz";

type CourseInfo = {
  id: string;
  title: string;
  category?: string;
  instructor_name?: string;
};

export default function StudentPlayPage({ params }: Props) {
  const { course_id } = params;
  const router = useRouter();
  const videoPlayerRef = useRef<VideoPlayerRef>(null);
  const [activeContent, setActiveContent] = useState<ContentType>("video");
  const [currentVideoTime, setCurrentVideoTime] = useState<number>(0);
  const [courseInfo, setCourseInfo] = useState<CourseInfo | null>(null);

  useEffect(() => {
    const fetchCourseInfo = async () => {
      try {
        const data = await apiGet<CourseInfo>(`/api/courses/${course_id}`);
        setCourseInfo(data);
      } catch (err) {
        console.error("강의 정보 가져오기 오류:", err);
        // 오류 시 기본값 설정
        setCourseInfo({ id: course_id, title: course_id });
      }
    };
    fetchCourseInfo();
  }, [course_id]);

  const handleTimestampClick = (timeInSeconds: number) => {
    if (videoPlayerRef.current) {
      videoPlayerRef.current.seekTo(timeInSeconds);
    }
  };

  const handleVideoTimeUpdate = (time: number) => {
    setCurrentVideoTime(time);
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 px-6 py-10 bg-white">
      <header className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-sm font-medium text-slate-700 transition-colors hover:text-slate-900"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>뒤로 가기</span>
          </button>
          <div className="rounded-full border border-blue-200 bg-blue-50 px-4 py-1 text-xs text-blue-700">
            AI 챗봇 자동 생성
          </div>
        </div>
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">
            강의 시청
          </p>
          <h1 className="text-2xl font-bold text-slate-900">
            {courseInfo?.title || "강의 로딩 중..."}
          </h1>
        </div>
      </header>

      {/* 토글 버튼 */}
      <div className="flex gap-2 rounded-lg border border-slate-200 bg-white p-1 shadow-sm">
        <button
          onClick={() => setActiveContent("video")}
          className={`flex-1 flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeContent === "video"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-600 hover:bg-slate-50"
          }`}
        >
          <Play className="w-4 h-4" />
          강의 시청
        </button>
        <button
          onClick={() => setActiveContent("summary")}
          className={`flex-1 flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeContent === "summary"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-600 hover:bg-slate-50"
          }`}
        >
          <FileText className="w-4 h-4" />
          요약노트
        </button>
        <button
          onClick={() => setActiveContent("quiz")}
          className={`flex-1 flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeContent === "quiz"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-600 hover:bg-slate-50"
          }`}
        >
          <PenTool className="w-4 h-4" />
          퀴즈
        </button>
      </div>

      {/* 컨텐츠 영역 */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* 강의 시청: 비디오 + 챗봇 */}
        {activeContent === "video" && (
          <>
            <div className="lg:col-span-2">
              <VideoPlayer
                ref={videoPlayerRef}
                src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/video/${course_id}`}
                onTimeUpdate={handleVideoTimeUpdate}
              />
            </div>
            <div className="lg:col-span-1">
              <div className="sticky top-6 h-[calc(100vh-15.5rem)]">
                <ChatPanel
                  courseId={course_id}
                  courseTitle={courseInfo?.title}
                  onTimestampClick={handleTimestampClick}
                  currentTime={currentVideoTime}
                />
              </div>
            </div>
          </>
        )}

        {/* 요약노트: 전체 너비 */}
        {activeContent === "summary" && (
          <div className="lg:col-span-3">
            <div className="h-[calc(100vh-12rem)]">
              <SummaryNote courseId={course_id} />
            </div>
          </div>
        )}

        {/* 퀴즈: 전체 너비 */}
        {activeContent === "quiz" && (
          <div className="lg:col-span-3">
            <div className="h-[calc(100vh-12rem)]">
              <Quiz courseId={course_id} />
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

