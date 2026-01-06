import Link from "next/link";
import ChatPanel from "../components/ChatPanel";
import VideoPlayer from "../components/VideoPlayer";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-4 px-6 py-10 bg-white">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">
            Yeop-Gang
          </p>
          <h1 className="text-2xl font-bold text-slate-900">
            EBS 인강 AI 튜터
          </h1>
        </div>
        <div className="rounded-full border border-blue-200 bg-blue-50 px-4 py-1 text-xs text-blue-700">
          초기 데모 레이아웃
        </div>
      </header>

      <div className="flex gap-3 text-sm">
        <Link
          className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 transition-colors"
          href="/instructor/upload"
        >
          강사용 업로드
        </Link>
        <Link
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-slate-700 hover:bg-slate-50 transition-colors"
          href="/student"
        >
          학생용 강의 목록
        </Link>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <VideoPlayer />
        </div>
        <div className="h-[520px] lg:col-span-1">
          <ChatPanel courseId="demo-course" />
        </div>
      </div>
    </main>
  );
}

