"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Upload } from "lucide-react";
import UploadForm from "../../../components/UploadForm";

export default function InstructorUploadPage() {
  const router = useRouter();

  const handleUploadSuccess = (courseId: string) => {
    // 업로드 성공 후 학생용 페이지로 이동
    router.push(`/student/play/${courseId}`);
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="mx-auto max-w-4xl px-6 py-10">
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
            </div>
          </div>
        </div>

        {/* 업로드 폼 */}
        <UploadForm onSubmitted={handleUploadSuccess} />
      </div>
    </main>
  );
}
