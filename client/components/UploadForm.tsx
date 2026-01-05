"use client";

import { useState, useEffect, useRef } from "react";
import ProgressBar from "./ProgressBar";

type Props = {
  onSubmitted?: (courseId: string) => void;
};

// API 기본 URL (환경 변수 또는 기본값)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type StatusResponse = {
  course_id: string;
  status: string;
  progress: number;
  message?: string;
};

export default function UploadForm({ onSubmitted }: Props) {
  const [instructorId, setInstructorId] = useState("");
  const [courseId, setCourseId] = useState("");
  const [video, setVideo] = useState<File | null>(null);
  const [audio, setAudio] = useState<File | null>(null);
  const [pdf, setPdf] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");
  const [progress, setProgress] = useState<number>(0);
  const [progressMessage, setProgressMessage] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // 진행도 폴링 함수
  const pollStatus = async (currentCourseId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/status/${currentCourseId}`);
      if (!res.ok) {
        console.error("Status check failed:", res.status);
        return;
      }

      const data: StatusResponse = await res.json();
      setProgress(data.progress);
      
      if (data.status === "completed") {
        setIsProcessing(false);
        setStatus(`처리 완료! (${data.progress}%)`);
        setProgressMessage("처리 완료");
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        // 완료 후 약간의 지연을 두고 콜백 호출
        setTimeout(() => {
          onSubmitted?.(currentCourseId);
        }, 1000);
      } else if (data.status === "failed") {
        setIsProcessing(false);
        setStatus(`처리 실패: ${data.message || "알 수 없는 오류"}`);
        setProgressMessage("처리 실패");
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      } else if (data.status === "processing") {
        // 처리 중인 상태이면 계속 폴링
        setStatus(`처리 중... (${data.progress}%)`);
        if (data.message) {
          setProgressMessage(data.message);
        }
      }
    } catch (err) {
      console.error("Status polling error:", err);
    }
  };

  // 컴포넌트 언마운트 시 폴링 정리
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const handleSubmit = async () => {
    if (!instructorId || !courseId) {
      setStatus("instructorId와 courseId를 입력하세요.");
      return;
    }
    const form = new FormData();
    form.append("instructor_id", instructorId);
    form.append("course_id", courseId);
    if (video) form.append("video", video);
    if (audio) form.append("audio", audio);
    if (pdf) form.append("pdf", pdf);

    setStatus("파일 업로드 중...");
    setProgress(0);
    setProgressMessage("업로드 중...");
    setIsProcessing(true);

    try {
      // 절대 경로로 백엔드 서버에 요청
      const res = await fetch(`${API_BASE_URL}/api/upload`, {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`업로드 실패: ${res.status} ${errorText}`);
      }

      const json = await res.json();
      setStatus("업로드 완료. 처리 시작 중...");
      setProgress(5);
      setProgressMessage("업로드 완료, 처리 대기 중...");

      // 업로드 성공 후 진행도 폴링 시작 (2초마다 확인)
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
      
      // 즉시 한 번 확인
      pollStatus(courseId);
      
      // 그 다음부터는 2초마다 확인
      pollingIntervalRef.current = setInterval(() => {
        pollStatus(courseId);
      }, 2000);
    } catch (err) {
      console.error("업로드 오류:", err);
      const errorMessage =
        err instanceof Error ? err.message : "알 수 없는 오류";
      setStatus(
        `업로드 실패: ${errorMessage}. 백엔드 서버(${API_BASE_URL})가 실행 중인지 확인하세요.`
      );
      setProgress(0);
      setProgressMessage("");
      setIsProcessing(false);
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    }
  };

  return (
    <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="text-sm font-semibold text-slate-200">강사용 업로드</div>
      <input
        className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500"
        placeholder="Instructor ID"
        value={instructorId}
        onChange={(e) => setInstructorId(e.target.value)}
      />
      <input
        className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500"
        placeholder="Course ID"
        value={courseId}
        onChange={(e) => setCourseId(e.target.value)}
      />
      <div className="space-y-2 text-sm text-slate-200">
        <label className="block">
          <span className="text-slate-400">비디오 (MP4 등)</span>
          <input
            type="file"
            accept="video/*,.mp4,.avi,.mov,.mkv,.webm"
            className="mt-1 w-full text-xs text-slate-300"
            onChange={(e) => setVideo(e.target.files?.[0] ?? null)}
          />
        </label>
        <label className="block">
          <span className="text-slate-400">오디오 (MP3 등)</span>
          <input
            type="file"
            accept="audio/*,.mp3,.wav,.m4a,.aac,.ogg,.flac"
            className="mt-1 w-full text-xs text-slate-300"
            onChange={(e) => setAudio(e.target.files?.[0] ?? null)}
          />
        </label>
        <label className="block">
          <span className="text-slate-400">PDF (선택)</span>
          <input
            type="file"
            accept="application/pdf"
            className="mt-1 w-full text-xs text-slate-300"
            onChange={(e) => setPdf(e.target.files?.[0] ?? null)}
          />
        </label>
      </div>
      <button
        className="w-full rounded-lg bg-sky-500 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-sky-600 disabled:bg-slate-600 disabled:cursor-not-allowed"
        onClick={handleSubmit}
        disabled={isProcessing}
      >
        {isProcessing ? "처리 중..." : "업로드"}
      </button>
      
      {/* 진행도 바 표시 */}
      {isProcessing && (
        <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-4">
          <ProgressBar progress={progress} message={progressMessage} />
        </div>
      )}
      
      {status && (
        <div
          className={`rounded-lg px-4 py-3 text-sm ${
            status.includes("완료") && !isProcessing
              ? "bg-green-900/50 text-green-200 border border-green-800"
              : status.includes("실패") || status.includes("오류")
              ? "bg-red-900/50 text-red-200 border border-red-800"
              : "bg-slate-800 text-slate-200 border border-slate-700"
          }`}
        >
          {status}
        </div>
      )}
    </div>
  );
}
