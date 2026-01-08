"use client";

import { useRef, useState, useImperativeHandle, forwardRef, useEffect } from "react";
import { AlertCircle, Loader2 } from "lucide-react";

type Props = {
  src?: string;
  onTimeUpdate?: (currentTime: number) => void;
};

export type VideoPlayerRef = {
  seekTo: (time: number) => void;
};

const VideoPlayer = forwardRef<VideoPlayerRef, Props>(({ src, onTimeUpdate }, ref) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 외부에서 호출 가능한 함수 노출
  useImperativeHandle(ref, () => ({
    seekTo: (time: number) => {
      if (videoRef.current) {
        videoRef.current.currentTime = time;
        setCurrentTime(time);
      }
    },
  }));

  const handleTimeUpdate = () => {
    if (videoRef.current && !isDragging) {
      const time = videoRef.current.currentTime;
      setCurrentTime(time);
      // 부모 컴포넌트에 현재 시간 전달
      if (onTimeUpdate) {
        onTimeUpdate(time);
      }
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
      setIsLoading(false);
      setError(null);
    }
  };

  const handleError = (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    setIsLoading(false);
    const video = e.currentTarget;
    let errorMsg = "비디오를 로드할 수 없습니다.";
    
    if (video.error) {
      switch (video.error.code) {
        case video.error.MEDIA_ERR_ABORTED:
          errorMsg = "비디오 로드가 중단되었습니다.";
          break;
        case video.error.MEDIA_ERR_NETWORK:
          errorMsg = "네트워크 오류로 비디오를 로드할 수 없습니다.";
          break;
        case video.error.MEDIA_ERR_DECODE:
          errorMsg = "비디오 디코딩 오류가 발생했습니다.";
          break;
        case video.error.MEDIA_ERR_SRC_NOT_SUPPORTED:
          errorMsg = "비디오 형식이 지원되지 않습니다.";
          break;
      }
    }
    setError(errorMsg);
    console.error("Video error:", video.error, "src:", src);
  };

  const handleLoadStart = () => {
    setIsLoading(true);
    setError(null);
  };

  // src가 변경되면 로딩 상태 초기화
  useEffect(() => {
    setIsLoading(true);
    setError(null);
  }, [src]);

  const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = parseFloat(e.target.value);
    setCurrentTime(newTime);
    if (videoRef.current) {
      videoRef.current.currentTime = newTime;
    }
  };

  const handleMouseDown = () => {
    setIsDragging(true);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="aspect-video w-full overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm relative">
      {/* 로딩 상태 */}
      {isLoading && !error && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900 z-10">
          <div className="flex flex-col items-center gap-3 text-white">
            <Loader2 className="h-8 w-8 animate-spin" />
            <span className="text-sm">비디오 로딩 중...</span>
          </div>
        </div>
      )}

      {/* 에러 상태 */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900 z-10">
          <div className="flex flex-col items-center gap-3 text-white p-6 text-center">
            <AlertCircle className="h-8 w-8 text-red-400" />
            <div>
              <p className="text-sm font-medium mb-1">{error}</p>
              <p className="text-xs text-slate-400">URL: {src}</p>
            </div>
            <button
              onClick={() => {
                setError(null);
                setIsLoading(true);
                if (videoRef.current) {
                  videoRef.current.load();
                }
              }}
              className="mt-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
            >
              다시 시도
            </button>
          </div>
        </div>
      )}

      <video
        ref={videoRef}
        className="h-full w-full bg-black"
        controls
        src={src ?? `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/video/default`}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onError={handleError}
        onLoadStart={handleLoadStart}
        preload="metadata"
        playsInline
      />
      {/* 커스텀 타임라인 컨트롤 */}
      <div className="relative w-full bg-slate-50 border-t border-slate-200 px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-600 min-w-[40px]">
            {formatTime(currentTime)}
          </span>
          <input
            type="range"
            min="0"
            max={duration || 0}
            step="0.1"
            value={currentTime}
            onChange={handleProgressChange}
            onMouseDown={handleMouseDown}
            onMouseUp={handleMouseUp}
            onTouchStart={handleMouseDown}
            onTouchEnd={handleMouseUp}
            className="flex-1 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            style={{
              background: `linear-gradient(to right, rgb(37 99 235) 0%, rgb(37 99 235) ${
                duration ? (currentTime / duration) * 100 : 0
              }%, rgb(226 232 240) ${
                duration ? (currentTime / duration) * 100 : 0
              }%, rgb(226 232 240) 100%)`,
            }}
          />
          <span className="text-xs text-slate-600 min-w-[40px]">
            {formatTime(duration)}
          </span>
        </div>
      </div>
    </div>
  );
});

VideoPlayer.displayName = "VideoPlayer";

export default VideoPlayer;

