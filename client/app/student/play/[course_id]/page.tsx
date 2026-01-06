"use client";

import { useRef, useState } from "react";
import { Play, FileText, PenTool } from "lucide-react";
import ChatPanel from "../../../../components/ChatPanel";
import SummaryNote from "../../../../components/SummaryNote";
import Quiz from "../../../../components/Quiz";
import VideoPlayer, { VideoPlayerRef } from "../../../../components/VideoPlayer";

type Props = {
  params: { course_id: string };
};

type ContentType = "video" | "summary" | "quiz";

export default function StudentPlayPage({ params }: Props) {
  const { course_id } = params;
  const videoPlayerRef = useRef<VideoPlayerRef>(null);
  const [activeContent, setActiveContent] = useState<ContentType>("video");

  const handleTimestampClick = (timeInSeconds: number) => {
    if (videoPlayerRef.current) {
      videoPlayerRef.current.seekTo(timeInSeconds);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 px-6 py-10 bg-white">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">
            Course
          </p>
          <h1 className="text-2xl font-bold text-slate-900">
            강의 플레이 · {course_id}
          </h1>
        </div>
        <div className="rounded-full border border-blue-200 bg-blue-50 px-4 py-1 text-xs text-blue-700">
          AI 챗봇 자동 생성
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
              />
            </div>
            <div className="lg:col-span-1">
              <div className="sticky top-6 h-[calc(100vh-6rem)]">
                <ChatPanel
                  courseId={course_id}
                  onTimestampClick={handleTimestampClick}
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

