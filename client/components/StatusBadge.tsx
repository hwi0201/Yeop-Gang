"use client";

type Props = {
  courseId: string;
  status?: string;
  progress?: number;
};

export default function StatusBadge({ courseId, status, progress }: Props) {
  return (
    <div className="flex items-center gap-2 text-xs text-slate-200">
      <span className="rounded-full bg-slate-800 px-2 py-1">{courseId}</span>
      <span className="rounded-full bg-sky-900/50 px-2 py-1">
        {status ?? "unknown"}
      </span>
      {typeof progress === "number" && (
        <span className="rounded-full bg-slate-800 px-2 py-1">
          {progress}%
        </span>
      )}
    </div>
  );
}

