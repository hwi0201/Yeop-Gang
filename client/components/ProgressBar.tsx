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
        <div className="text-xs text-slate-600">{message}</div>
      )}
      <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden relative">
        <div
          className="h-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-300 ease-out rounded-full flex items-center justify-end pr-2 relative"
          style={{ width: `${clampedProgress}%` }}
        >
          {/* 로딩 애니메이션 (진행 중일 때) */}
          {clampedProgress > 0 && clampedProgress < 100 && (
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"></div>
          )}
          {clampedProgress > 10 && (
            <span className="text-xs font-semibold text-white relative z-10">
              {clampedProgress.toFixed(0)}%
            </span>
          )}
        </div>
      </div>
      {clampedProgress <= 10 && (
        <div className="text-xs text-slate-600 text-right">
          {clampedProgress.toFixed(0)}%
        </div>
      )}
    </div>
  );
}

