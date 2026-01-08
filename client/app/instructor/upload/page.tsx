"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Upload, AlertCircle, Loader2 } from "lucide-react";
import UploadForm from "../../../components/UploadForm";

export default function InstructorUploadPage() {
  const router = useRouter();
  const [isChecking, setIsChecking] = useState(true);
  const [instructorId, setInstructorId] = useState<string | null>(null);

  useEffect(() => {
    // 로그인 확인
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("instructor_token");
      const id = localStorage.getItem("instructor_id");
      
      if (!token || !id) {
        // 로그인하지 않았으면 로그인 페이지로 리다이렉트
        router.push("/instructor/login");
        return;
      }
      
      setInstructorId(id);
      setIsChecking(false);
    }
  }, [router]);

  const handleUploadSuccess = (courseId: string) => {
    // 업로드 성공 후 학생용 페이지로 이동
    router.push(`/student/play/${courseId}`);
  };

  if (isChecking) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
        <div className="mx-auto max-w-4xl px-6 py-10">
          <div className="flex flex-col items-center justify-center gap-4 py-16">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <span className="text-sm text-slate-600">로그인 확인 중...</span>
          </div>
        </div>
      </main>
    );
  }

  if (!instructorId) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
        <div className="mx-auto max-w-4xl px-6 py-10">
          <div className="rounded-xl border border-red-200 bg-red-50 p-6">
            <div className="mb-4 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-600" />
              <div className="flex-1">
                <h3 className="mb-1 text-sm font-semibold text-red-900">로그인 필요</h3>
                <p className="text-sm text-red-700">강의를 업로드하려면 로그인이 필요합니다.</p>
              </div>
            </div>
            <Link
              href="/instructor/login"
              className="inline-block rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
            >
              로그인하기
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="mx-auto max-w-4xl px-6 py-10">
        {/* 네비게이션 */}
        <div className="mb-8 flex items-center justify-between">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-slate-600 transition-colors hover:text-slate-900"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>홈으로</span>
          </Link>
          <Link
            href="/instructor/courses"
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-blue-500 hover:bg-blue-50"
          >
            <span>내 강의 관리</span>
          </Link>
        </div>

        {/* 헤더 */}
        <div className="mb-8">
          <div className="mb-3 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
              <Upload className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-slate-900">강의 업로드</h1>
              <p className="mt-1 text-sm text-slate-500">
                새로운 강의를 등록하고 학습 자료를 업로드하세요
              </p>
              <p className="mt-1 text-xs text-slate-400">
                로그인된 강사: <span className="font-medium text-slate-600">{instructorId}</span>
              </p>
            </div>
          </div>
        </div>

        {/* 업로드 폼 */}
        <UploadForm instructorId={instructorId} onSubmitted={handleUploadSuccess} />
      </div>
    </main>
  );
}
