"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, LogIn, AlertCircle, Loader2 } from "lucide-react";
import { apiPost, handleApiError } from "../../../lib/api";

export default function InstructorLoginPage() {
  const router = useRouter();
  const [instructorId, setInstructorId] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    if (!instructorId.trim()) {
      setError("강사 ID를 입력해주세요.");
      setIsLoading(false);
      return;
    }

    try {
      // 강사 로그인 API 호출 (강사가 없으면 자동 생성)
      const response = await apiPost<{
        access_token: string;
        user_id: string;
        role: string;
      }>("/api/auth/login", {
        user_id: instructorId.trim(),
        password: "", // 비밀번호는 현재 사용하지 않음
        role: "instructor",
      });

      // 로컬 스토리지에 토큰 저장
      if (typeof window !== "undefined") {
        localStorage.setItem("instructor_token", response.access_token);
        localStorage.setItem("instructor_id", response.user_id);
      }

      // 강사 페이지로 이동 (강의 관리 페이지)
      router.push("/instructor/courses");
    } catch (err) {
      console.error("강사 로그인 오류:", err);
      const apiError = handleApiError(err);
      setError(apiError.message || "로그인에 실패했습니다. 강사 ID를 확인해주세요.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="mx-auto max-w-md px-6 py-16">
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

        {/* 로그인 폼 */}
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-lg">
          <div className="mb-8 text-center">
            <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 text-blue-600">
              <LogIn className="h-8 w-8" />
            </div>
            <h1 className="mb-2 text-2xl font-bold text-slate-900">강사 로그인</h1>
            <p className="text-sm text-slate-600">
              강사 ID를 입력하여 강의 업로드 페이지로 이동하세요
            </p>
          </div>

          {error && (
            <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-600" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-red-900">오류 발생</p>
                  <p className="mt-1 text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label
                htmlFor="instructorId"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                강사 ID
              </label>
              <input
                id="instructorId"
                type="text"
                value={instructorId}
                onChange={(e) => setInstructorId(e.target.value)}
                placeholder="강사 ID를 입력하세요"
                disabled={isLoading}
                className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 placeholder-slate-400 transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:bg-slate-50 disabled:text-slate-500"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>로그인 중...</span>
                </span>
              ) : (
                <span>로그인</span>
              )}
            </button>
          </form>
        </div>
      </div>
    </main>
  );
}
