"use client";

import { useMemo, useState } from "react";
import type { ChatMessage } from "../lib/types";

type Props = {
  courseId: string;
};

export default function ChatPanel({ courseId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: `코스 ${courseId} 채팅을 시작합니다. 질문을 입력하세요.`,
    },
  ]);
  const [input, setInput] = useState("");

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: trimmed },
      { role: "assistant", content: "응답 예시: 백엔드 연결 예정입니다." },
    ]);
    setInput("");
  };

  const transcript = useMemo(
    () => messages.map((m, idx) => ({ ...m, id: `msg-${idx}` })),
    [messages],
  );

  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-800 bg-slate-950/60">
      <div className="border-b border-slate-800 px-4 py-3 text-sm font-semibold text-slate-200">
        실시간 채팅 · {courseId}
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3 text-sm">
        {transcript.map((msg) => (
          <div key={msg.id} className="space-y-1">
            <div className="text-xs uppercase tracking-wide text-slate-400">
              {msg.role === "assistant" ? "옆강 봇" : "나"}
            </div>
            <div
              className={`rounded-lg border px-3 py-2 ${
                msg.role === "assistant"
                  ? "border-sky-900/60 bg-sky-900/30"
                  : "border-slate-800 bg-slate-900/60"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
      </div>
      <div className="border-t border-slate-800 p-3">
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500"
            placeholder="질문을 입력하세요..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSend();
            }}
          />
          <button
            className="rounded-lg bg-sky-500 px-4 text-sm font-semibold text-white shadow hover:bg-sky-600"
            onClick={handleSend}
          >
            전송
          </button>
        </div>
      </div>
    </div>
  );
}

