"use client";

import { useMemo, useState } from "react";
import type { ChatMessage } from "../lib/types";

type Props = {
  courseId: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ChatPanel({ courseId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: `코스 ${courseId} 채팅을 시작합니다. 질문을 입력하세요.`,
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId] = useState(() => `conv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    // 사용자 메시지 즉시 추가
    const userMessage: ChatMessage = { role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          course_id: courseId,
          question: trimmed,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) {
        throw new Error(`API 오류: ${response.status}`);
      }

      const data = await response.json();
      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: data.answer || "답변을 받을 수 없습니다.",
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("채팅 API 오류:", error);
      const errorMessage: ChatMessage = {
        role: "assistant",
        content: `오류가 발생했습니다: ${error instanceof Error ? error.message : "알 수 없는 오류"}. 백엔드 서버가 실행 중인지 확인하세요.`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
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
            className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500 disabled:opacity-50"
            placeholder={isLoading ? "답변 대기 중..." : "질문을 입력하세요..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !isLoading) handleSend();
            }}
            disabled={isLoading}
          />
          <button
            className="rounded-lg bg-sky-500 px-4 text-sm font-semibold text-white shadow hover:bg-sky-600 disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
          >
            {isLoading ? "전송 중..." : "전송"}
          </button>
        </div>
      </div>
    </div>
  );
}

