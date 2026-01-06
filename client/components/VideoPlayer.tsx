"use client";

import { useRef, useState, useImperativeHandle, forwardRef } from "react";

type Props = {
  src?: string;
};

export type VideoPlayerRef = {
  seekTo: (time: number) => void;
};

const VideoPlayer = forwardRef<VideoPlayerRef, Props>(({ src }, ref) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isDragging, setIsDragging] = useState(false);

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
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

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
    <div className="aspect-video w-full overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <video
        ref={videoRef}
        className="h-full w-full bg-black"
        controls
        src={src ?? `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/video/default`}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
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

