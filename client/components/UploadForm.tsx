"use client";

import { useState, useEffect, useRef } from "react";
import ProgressBar from "./ProgressBar";
import { API_BASE_URL, apiGet, apiUpload, handleApiError } from "../lib/api";

type Props = {
  onSubmitted?: (courseId: string) => void;
};

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
  const [uploadError, setUploadError] = useState<string | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // 진행도 폴링 함수
  const pollStatus = async (currentCourseId: string) => {
    try {
      const data = await apiGet<StatusResponse>(`/api/status/${currentCourseId}`);
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
        let errorMsg = data.message || "알 수 없는 오류가 발생했습니다. 백엔드 서버 로그를 확인하세요.";
        // "처리 실패:" 중복 제거
        if (errorMsg.startsWith("처리 실패:")) {
          errorMsg = errorMsg.replace("처리 실패:", "").trim();
        }
        setStatus(`처리 실패: ${errorMsg}`);
        setProgressMessage("처리 실패");
        setUploadError(errorMsg);
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
      setUploadError(null);
      return;
    }
    
    // 에러 상태 초기화
    setUploadError(null);
    
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
      const json = await apiUpload<{ course_id: string; instructor_id: string; status: string }>(
        "/api/upload",
        form
      );
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
      
      const apiError = handleApiError(err);
      const errorMessage = apiError.message;
      
      setUploadError(errorMessage);
      setStatus(`업로드 실패: ${errorMessage}`);
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
    <div className="space-y-3 rounded-xl border border-slate-200 bg-white shadow-sm p-4">
      <div className="text-sm font-semibold text-slate-900">강사용 업로드</div>
      <input
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        placeholder="Instructor ID"
        value={instructorId}
        onChange={(e) => setInstructorId(e.target.value)}
      />
      <input
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        placeholder="Course ID"
        value={courseId}
        onChange={(e) => setCourseId(e.target.value)}
      />
      <div className="space-y-2 text-sm">
        <label className="block">
          <span className="text-slate-600">비디오 (MP4 등)</span>
          <input
            type="file"
            accept="video/*,.mp4,.avi,.mov,.mkv,.webm"
            className="mt-1 w-full text-xs text-slate-700"
            onChange={(e) => setVideo(e.target.files?.[0] ?? null)}
          />
        </label>
        <label className="block">
          <span className="text-slate-600">오디오 (MP3 등)</span>
          <input
            type="file"
            accept="audio/*,.mp3,.wav,.m4a,.aac,.ogg,.flac"
            className="mt-1 w-full text-xs text-slate-700"
            onChange={(e) => setAudio(e.target.files?.[0] ?? null)}
          />
        </label>
        <label className="block">
          <span className="text-slate-600">PDF (선택)</span>
          <input
            type="file"
            accept="application/pdf"
            className="mt-1 w-full text-xs text-slate-700"
            onChange={(e) => setPdf(e.target.files?.[0] ?? null)}
          />
        </label>
      </div>
      <button
        className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:bg-slate-400 disabled:cursor-not-allowed transition-colors"
        onClick={handleSubmit}
        disabled={isProcessing}
      >
        {isProcessing ? "처리 중..." : "업로드"}
      </button>
      
      {/* 진행도 바 표시 */}
      {isProcessing && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <ProgressBar progress={progress} message={progressMessage} />
        </div>
      )}
      
      {status && (
        <div
          className={`rounded-lg px-4 py-3 text-sm ${
            status.includes("완료") && !isProcessing
              ? "bg-green-50 text-green-700 border border-green-200"
              : status.includes("실패") || status.includes("오류")
              ? "bg-red-50 text-red-700 border border-red-200"
              : "bg-slate-50 text-slate-700 border border-slate-200"
          }`}
        >
          <div className="flex items-center justify-between">
            <span>{status}</span>
            {uploadError && !isProcessing && (
              <button
                onClick={handleSubmit}
                className="ml-2 rounded-md bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700 transition-colors"
              >
                다시 시도
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
