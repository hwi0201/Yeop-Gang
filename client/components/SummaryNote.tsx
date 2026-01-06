"use client";

import { useState, useEffect } from "react";
import { FileText, Key, AlertCircle, RefreshCw } from "lucide-react";
import { apiPost, handleApiError } from "../lib/api";

type Props = {
  courseId: string;
};

type SummaryResponse = {
  summary: string;
  key_points: string[];
  created_at?: string;
};

export default function SummaryNote({ courseId }: Props) {
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await apiPost<SummaryResponse>("/api/summary", {
        course_id: courseId,
      });
      
      setSummary({
        summary: data.summary,
        key_points: data.key_points || [],
      });
    } catch (err) {
      console.error("요약 생성 오류:", err);
      const apiError = handleApiError(err);
      setError(apiError.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // 컴포넌트 마운트 시 자동으로 요약 생성
    fetchSummary();
  }, [courseId]);

  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-900">
        강의 요약노트 · {courseId}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {isLoading && (
          <div className="flex flex-col items-center justify-center gap-3 py-8">
            <div className="flex gap-1">
              <div className="h-2 w-2 animate-bounce rounded-full bg-blue-500 [animation-delay:-0.3s]"></div>
              <div className="h-2 w-2 animate-bounce rounded-full bg-blue-500 [animation-delay:-0.15s]"></div>
              <div className="h-2 w-2 animate-bounce rounded-full bg-blue-500"></div>
            </div>
            <span className="text-xs text-slate-500">요약 생성 중...</span>
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
            <div className="mb-2 flex items-center gap-2 text-sm text-red-700">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
            <button
              onClick={fetchSummary}
              className="w-full rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 transition-colors"
            >
              다시 시도
            </button>
          </div>
        )}

        {summary && !isLoading && (
          <div className="space-y-4">
            {/* 핵심 요약 */}
            <div>
              <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-900">
                <FileText className="w-4 h-4 text-blue-600" />
                핵심 요약
              </h3>
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-relaxed text-slate-700 whitespace-pre-wrap">
                {summary.summary}
              </div>
            </div>

            {/* 주요 포인트 */}
            {summary.key_points.length > 0 && (
              <div>
                <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-900">
                  <Key className="w-4 h-4 text-blue-600" />
                  주요 포인트
                </h3>
                <ul className="space-y-2">
                  {summary.key_points.map((point, idx) => (
                    <li
                      key={idx}
                      className="flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700"
                    >
                      <span className="mt-0.5 text-blue-600">•</span>
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {!summary && !isLoading && !error && (
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-center text-sm text-slate-500">
            <p>요약을 생성하려면 새로고침 버튼을 클릭하세요.</p>
            <button
              onClick={fetchSummary}
              className="mt-2 rounded-md bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-700 transition-colors"
            >
              요약 생성
            </button>
          </div>
        )}
      </div>

      <div className="border-t border-slate-200 bg-slate-50 px-4 py-3">
        <button
          onClick={fetchSummary}
          disabled={isLoading}
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              생성 중...
            </>
          ) : (
            <>
              <RefreshCw className="w-4 h-4" />
              요약 새로고침
            </>
          )}
        </button>
      </div>
    </div>
  );
}

