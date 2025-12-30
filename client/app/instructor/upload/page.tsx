import UploadForm from "../../../components/UploadForm";

export default function InstructorUploadPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-10">
      <div>
        <p className="text-xs uppercase tracking-widest text-slate-400">
          Instructor
        </p>
        <h1 className="text-2xl font-bold text-white">강의 업로드</h1>
        <p className="text-sm text-slate-300">
          비디오/PDF를 업로드하면 백그라운드에서 STT → 임베딩 → 페르소나가
          생성됩니다.
        </p>
      </div>
      <UploadForm />
    </main>
  );
}

