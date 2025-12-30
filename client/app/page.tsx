import Link from "next/link";
import ChatPanel from "../components/ChatPanel";
import VideoPlayer from "../components/VideoPlayer";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-4 px-6 py-10">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-400">
            Yeop-Gang
          </p>
          <h1 className="text-2xl font-bold text-white">
            EBS 인강 AI 보조 챗봇
          </h1>
        </div>
        <div className="rounded-full border border-sky-800 bg-sky-900/30 px-4 py-1 text-xs text-sky-200">
          초기 데모 레이아웃
        </div>
      </header>

      <div className="flex gap-3 text-sm text-slate-300">
        <Link
          className="rounded-lg bg-sky-600 px-4 py-2 font-semibold text-white"
          href="/instructor/upload"
        >
          강사용 업로드
        </Link>
        <Link
          className="rounded-lg border border-slate-700 px-4 py-2 text-slate-200"
          href="/student/play/demo-course"
        >
          학생용 데모 이동
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

