"use client";

type Props = {
  progress: number; // 0-100
  message?: string;
  className?: string;
};

export default function ProgressBar({ progress, message, className = "" }: Props) {
  const clampedProgress = Math.max(0, Math.min(100, progress));

  return (
    <div className={`space-y-2 ${className}`}>
      {message && (
        <div className="text-xs text-slate-400">{message}</div>
      )}
      <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-sky-500 to-sky-600 transition-all duration-300 ease-out rounded-full flex items-center justify-end pr-2"
          style={{ width: `${clampedProgress}%` }}
        >
          {clampedProgress > 10 && (
            <span className="text-xs font-semibold text-white">
              {clampedProgress.toFixed(0)}%
            </span>
          )}
        </div>
      </div>
      {clampedProgress <= 10 && (
        <div className="text-xs text-slate-400 text-right">
          {clampedProgress.toFixed(0)}%
        </div>
      )}
    </div>
  );
}

