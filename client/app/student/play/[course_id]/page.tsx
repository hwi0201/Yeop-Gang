import ChatPanel from "../../../../components/ChatPanel";
import VideoPlayer from "../../../../components/VideoPlayer";

type Props = {
  params: { course_id: string };
};

export default function StudentPlayPage({ params }: Props) {
  const { course_id } = params;

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-4 px-6 py-10">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-400">
            Course
          </p>
          <h1 className="text-2xl font-bold text-white">
            강의 플레이 · {course_id}
          </h1>
        </div>
        <div className="rounded-full border border-emerald-800 bg-emerald-900/30 px-4 py-1 text-xs text-emerald-200">
          AI 챗봇 자동 생성
        </div>
      </header>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <VideoPlayer />
        </div>
        <div className="h-[520px] lg:col-span-1">
          <ChatPanel courseId={course_id} />
        </div>
      </div>
    </main>
  );
}

