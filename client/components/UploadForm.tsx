"use client";

import { useState } from "react";

type Props = {
  onSubmitted?: (courseId: string) => void;
};

export default function UploadForm({ onSubmitted }: Props) {
  const [instructorId, setInstructorId] = useState("");
  const [courseId, setCourseId] = useState("");
  const [video, setVideo] = useState<File | null>(null);
  const [pdf, setPdf] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");

  const handleSubmit = async () => {
    if (!instructorId || !courseId) {
      setStatus("instructorId와 courseId를 입력하세요.");
      return;
    }
    const form = new FormData();
    form.append("instructor_id", instructorId);
    form.append("course_id", courseId);
    if (video) form.append("video", video);
    if (pdf) form.append("pdf", pdf);

    setStatus("업로드 중...");
    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error("upload failed");
      const json = await res.json();
      setStatus(`업로드 완료: 상태 ${json.status}`);
      onSubmitted?.(courseId);
    } catch (err) {
      setStatus("업로드 실패. 백엔드 실행 여부를 확인하세요.");
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
          <span className="text-slate-400">비디오</span>
          <input
            type="file"
            accept="video/*"
            className="mt-1 w-full text-xs text-slate-300"
            onChange={(e) => setVideo(e.target.files?.[0] ?? null)}
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
        className="w-full rounded-lg bg-sky-500 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-sky-600"
        onClick={handleSubmit}
      >
        업로드
      </button>
      {status && <div className="text-xs text-slate-300">{status}</div>}
    </div>
  );
}

