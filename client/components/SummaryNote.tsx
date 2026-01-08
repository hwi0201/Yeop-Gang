"use client";

import { useState, useEffect } from "react";
import { FileText, AlertCircle, RefreshCw } from "lucide-react";
import { apiPost, apiGet, handleApiError } from "../lib/api";
import { marked } from "marked";

type Props = {
  courseId: string;
};

type SummaryResponse = {
  summary: string;
  key_points: string[];
  created_at?: string;
};

type CourseInfo = {
  id: string;
  title: string;
  category?: string;
  instructor_name?: string;
};

export default function SummaryNote({ courseId }: Props) {
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [courseInfo, setCourseInfo] = useState<CourseInfo | null>(null);

  const fetchSummary = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await apiPost<SummaryResponse>("/api/summary", {
        course_id: courseId,
      });
      
      console.log("📝 Summary received:", data.summary?.substring(0, 200));
      console.log("📝 Full summary length:", data.summary?.length);
      
      // 마크다운을 HTML로 변환
      let summaryHtml = data.summary || "";
      
      // <pre><code class="language-markdown"> 태그로 감싸진 경우 제거
      if (summaryHtml.includes("<pre><code class=\"language-markdown\">") || 
          summaryHtml.includes("<pre><code class='language-markdown'>")) {
        console.log("🔧 코드 블록 태그 제거 중...");
        // <pre><code class="language-markdown"> 또는 <pre><code class='language-markdown'> 제거
        summaryHtml = summaryHtml
          .replace(/<pre><code class=["']language-markdown["']>/gi, "")
          .replace(/<\/code><\/pre>/gi, "")
          .trim();
        console.log("✅ 코드 블록 태그 제거 완료");
        console.log("📝 제거 후 샘플:", summaryHtml.substring(0, 100));
      }
      
      // HTML 태그가 이미 있으면 변환하지 않음 (단, <pre><code>는 제외)
      const isAlreadyHtml = (summaryHtml.trim().startsWith("<") && 
                           !summaryHtml.includes("##")) || 
                           (summaryHtml.includes("<h1") && !summaryHtml.includes("##")) || 
                           (summaryHtml.includes("<h2") && !summaryHtml.includes("##")) || 
                           (summaryHtml.includes("<p>") && !summaryHtml.includes("##")) || 
                           (summaryHtml.includes("<table>") && !summaryHtml.includes("|"));
      const isMarkdown = summaryHtml.includes("##") || 
                        summaryHtml.includes("**") || 
                        summaryHtml.includes("|") || 
                        summaryHtml.includes("- [") ||
                        summaryHtml.includes("```");
      
      console.log("📝 Is HTML?", isAlreadyHtml);
      console.log("📝 Is Markdown?", isMarkdown);
      console.log("📝 원본 샘플:", summaryHtml.substring(0, 100));
      
      if (summaryHtml && isMarkdown && !isAlreadyHtml) {
        // 마크다운 형식이면 HTML로 변환
        try {
          console.log("🔄 마크다운 → HTML 변환 시작...");
          console.log("🔄 원본 텍스트 길이:", summaryHtml.length);
          
          // marked.parse는 동기적으로 작동 (v17)
          marked.setOptions({
            breaks: true,
            gfm: true,
          });
          
          const parsed = marked.parse(summaryHtml);
          
          // marked.parse는 string을 반환
          if (typeof parsed === 'string') {
            summaryHtml = parsed;
          } else {
            // Promise인 경우 처리
            summaryHtml = await Promise.resolve(parsed);
          }
          
          console.log("✅ 프론트엔드에서 마크다운 → HTML 변환 완료");
          console.log("✅ 변환된 HTML 길이:", summaryHtml.length);
          console.log("✅ 변환된 HTML 샘플:", summaryHtml.substring(0, 300));
          console.log("✅ HTML 태그 포함?", summaryHtml.includes("<h") || summaryHtml.includes("<p>"));
        } catch (err) {
          console.error("❌ 마크다운 변환 오류:", err);
          console.error("❌ 오류 상세:", err);
          // 변환 실패 시 원본 유지
        }
      } else if (isAlreadyHtml) {
        console.log("ℹ️ 이미 HTML 형식입니다.");
      } else {
        console.log("ℹ️ 마크다운 형식이 아닙니다.");
      }
      
      setSummary({
        summary: summaryHtml,
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
    // 강의 정보 가져오기
    const fetchCourseInfo = async () => {
      try {
        const data = await apiGet<CourseInfo>(`/api/courses/${courseId}`);
        setCourseInfo(data);
      } catch (err) {
        console.error("강의 정보 가져오기 오류:", err);
        // 오류 시 기본값 설정
        setCourseInfo({ id: courseId, title: courseId });
      }
    };
    
    fetchCourseInfo();
    // 컴포넌트 마운트 시 자동으로 요약 생성
    fetchSummary();
  }, [courseId]);

  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-900">
        강의 요약노트 · {courseInfo?.title || "로딩 중..."}
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
          <div className="space-y-6">
            {/* 마크다운 요약노트 */}
            <div className="w-full">
              <div 
                className="rounded-lg border border-slate-200 bg-white px-6 py-5 text-sm leading-relaxed text-slate-700 overflow-x-hidden markdown-body"
                dangerouslySetInnerHTML={{ __html: summary.summary || "<p class='text-slate-500'>요약 내용이 없습니다.</p>" }}
              />
            </div>

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

