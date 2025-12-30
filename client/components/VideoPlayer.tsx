"use client";

type Props = {
  src?: string;
};

export default function VideoPlayer({ src }: Props) {
  return (
    <div className="aspect-video w-full overflow-hidden rounded-xl border border-slate-800 bg-black/40">
      <video
        className="h-full w-full bg-black"
        controls
        src={src ?? "https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"}
      />
    </div>
  );
}

