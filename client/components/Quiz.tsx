"use client";

import { useState, useEffect } from "react";
import { CheckCircle2, XCircle, Lightbulb, AlertCircle, Trophy, RefreshCw, Send } from "lucide-react";
import { apiPost, apiGet, handleApiError } from "../lib/api";

type Props = {
  courseId: string;
};

type CourseInfo = {
  id: string;
  title: string;
  category?: string;
  instructor_name?: string;
};

type QuizQuestion = {
  id: number;
  question: string;
  options: string[];
  correct_answer: number; // 0-based index
  explanation?: string;
};

type QuizResponse = {
  course_id?: string;
  questions: QuizQuestion[];
  quiz_id?: string;
};

type UserAnswer = {
  questionId: number;
  selectedOption: number | null;
};

type QuizResult = {
  course_id?: string;
  score: number;
  total: number;
  percentage: number;
  correct_answers?: number[];
  wrong_answers?: number[];
};

export default function Quiz({ courseId }: Props) {
  const [quiz, setQuiz] = useState<QuizResponse | null>(null);
  const [userAnswers, setUserAnswers] = useState<UserAnswer[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGraded, setIsGraded] = useState(false);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [courseInfo, setCourseInfo] = useState<CourseInfo | null>(null);

  const generateQuiz = async () => {
    setIsLoading(true);
    setError(null);
    setIsGraded(false);
    setUserAnswers([]);
    setResult(null);

    try {
      const data = await apiPost<QuizResponse>("/api/quiz/generate", {
        course_id: courseId,
        num_questions: 5,
      });
      
      if (!data.questions || data.questions.length === 0) {
        throw new Error("퀴즈를 생성할 수 없습니다. 다시 시도해주세요.");
      }

      setQuiz({ questions: data.questions, quiz_id: data.quiz_id });
      
      // 초기 답변 상태 설정
      setUserAnswers(
        data.questions.map((q) => ({
          questionId: q.id,
          selectedOption: null,
        }))
      );
    } catch (err) {
      console.error("퀴즈 생성 오류:", err);
      const apiError = handleApiError(err);
      setError(apiError.message);
    } finally {
      setIsLoading(false);
    }
  };

  const parseQuizFromAnswer = (answer: string): QuizQuestion[] => {
    const questions: QuizQuestion[] = [];
    const lines = answer.split("\n").map((line) => line.trim());

    let currentQuestion: Partial<QuizQuestion> | null = null;
    let questionId = 1;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // 문제 시작
      if (line.match(/^문제\d+[:：]/) || line.match(/^\d+\./)) {
        if (currentQuestion && currentQuestion.question) {
          questions.push(currentQuestion as QuizQuestion);
        }
        currentQuestion = {
          id: questionId++,
          question: line.replace(/^문제\d+[:：]\s*/, "").replace(/^\d+\.\s*/, ""),
          options: [],
          correct_answer: 0,
        };
      }
      // 선택지
      else if (line.match(/^[선택지\d+][:：]/) || line.match(/^[A-D][\.\)]/)) {
        if (currentQuestion) {
          const option = line
            .replace(/^선택지\d+[:：]\s*/, "")
            .replace(/^\d+[\.\)]\s*/, "")
            .replace(/^[A-D][\.\)]\s*/, "");
          currentQuestion.options.push(option);
        }
      }
      // 정답
      else if (line.match(/^정답[:：]/)) {
        if (currentQuestion) {
          const answerMatch = line.match(/정답[:：]\s*(\d+|[A-D])/);
          if (answerMatch) {
            const answerStr = answerMatch[1];
            if (answerStr.match(/[A-D]/)) {
              currentQuestion.correct_answer = answerStr.charCodeAt(0) - 65; // A=0, B=1, C=2, D=3
            } else {
              currentQuestion.correct_answer = parseInt(answerStr) - 1; // 1-based to 0-based
            }
          }
        }
      }
      // 일반 텍스트 (문제 내용에 추가)
      else if (line && currentQuestion && !currentQuestion.question.includes(line)) {
        if (currentQuestion.options.length === 0) {
          currentQuestion.question += " " + line;
        }
      }
    }

    // 마지막 문제 추가
    if (currentQuestion && currentQuestion.question && currentQuestion.options.length >= 2) {
      // 선택지가 4개가 아니면 채우기
      while (currentQuestion.options.length < 4) {
        currentQuestion.options.push(`선택지 ${currentQuestion.options.length + 1}`);
      }
      questions.push(currentQuestion as QuizQuestion);
    }

    // 최대 5문제로 제한
    return questions.slice(0, 5);
  };

  const handleAnswerSelect = (questionId: number, optionIndex: number) => {
    if (isGraded) return; // 채점 후에는 수정 불가

    setUserAnswers((prev) =>
      prev.map((answer) =>
        answer.questionId === questionId
          ? { ...answer, selectedOption: optionIndex }
          : answer
      )
    );
  };

  const handleSubmit = async () => {
    if (!quiz) return;

    // 모든 문제에 답변했는지 확인
    const allAnswered = userAnswers.every(
      (answer) => answer.selectedOption !== null
    );

    if (!allAnswered) {
      alert("모든 문제에 답변해주세요!");
      return;
    }

    setIsSubmitting(true);

    try {
      // 답변을 딕셔너리 형식으로 변환
      const answers: { [key: number]: number } = {};
      userAnswers.forEach((answer) => {
        if (answer.selectedOption !== null) {
          answers[answer.questionId] = answer.selectedOption;
        }
      });

      // 퀴즈 데이터를 함께 보내서 정확한 채점 보장
      const data = await apiPost<QuizResult>("/api/quiz/submit", {
        course_id: courseId,
        quiz_id: quiz.quiz_id,
        answers: answers,
        questions: quiz.questions, // 퀴즈 데이터 전송
      });

      setResult({
        score: data.score,
        total: data.total,
        percentage: data.percentage,
        correct_answers: data.correct_answers || [],
        wrong_answers: data.wrong_answers || [],
      });

      setIsGraded(true);
    } catch (err) {
      console.error("채점 오류:", err);
      // API 실패 시 로컬 채점으로 폴백
      const correctAnswers: number[] = [];
      const wrongAnswers: number[] = [];

      quiz.questions.forEach((question) => {
        const userAnswer = userAnswers.find(
          (a) => a.questionId === question.id
        );
        if (
          userAnswer &&
          userAnswer.selectedOption === question.correct_answer
        ) {
          correctAnswers.push(question.id);
        } else {
          wrongAnswers.push(question.id);
        }
      });

      const score = correctAnswers.length;
      const total = quiz.questions.length;
      const percentage = Math.round((score / total) * 100);

      setResult({
        score,
        total,
        percentage,
        correct_answers: correctAnswers,
        wrong_answers: wrongAnswers,
      });

      setIsGraded(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setQuiz(null);
    setUserAnswers([]);
    setIsGraded(false);
    setResult(null);
    setError(null);
  };

  useEffect(() => {
    // 강의 정보 가져오기
    const fetchCourseInfo = async () => {
      try {
        const data = await apiGet<CourseInfo>(`/api/courses/${courseId}`);
        setCourseInfo(data);
      } catch (err) {
        console.error("강의 정보 가져오기 오류:", err);
        // 오류 시 기본값 설정
        setCourseInfo({ id: courseId, title: courseId });
      }
    };
    
    fetchCourseInfo();
    // 컴포넌트 마운트 시 자동으로 퀴즈 생성
    generateQuiz();
  }, [courseId]);

  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-900">
        강의 퀴즈 · {courseInfo?.title || "로딩 중..."}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {isLoading && (
          <div className="flex flex-col items-center justify-center gap-3 py-8">
            <div className="flex gap-1">
              <div className="h-2 w-2 animate-bounce rounded-full bg-blue-500 [animation-delay:-0.3s]"></div>
              <div className="h-2 w-2 animate-bounce rounded-full bg-blue-500 [animation-delay:-0.15s]"></div>
              <div className="h-2 w-2 animate-bounce rounded-full bg-blue-500"></div>
            </div>
            <span className="text-xs text-slate-500">퀴즈 생성 중...</span>
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
            <div className="mb-2 flex items-center gap-2 text-sm text-red-700">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
            <button
              onClick={generateQuiz}
              className="w-full rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 transition-colors"
            >
              다시 시도
            </button>
          </div>
        )}

        {quiz && quiz.questions.length > 0 && (
          <div className="space-y-6">
            {quiz.questions.map((question, qIdx) => {
              const userAnswer = userAnswers.find(
                (a) => a.questionId === question.id
              );
              const isCorrect =
                isGraded &&
                userAnswer?.selectedOption === question.correct_answer;
              const isWrong =
                isGraded &&
                userAnswer?.selectedOption !== null &&
                userAnswer?.selectedOption !== question.correct_answer;

              return (
                <div
                  key={question.id}
                  className={`rounded-lg border px-4 py-3 ${
                    isCorrect
                      ? "border-green-200 bg-green-50"
                      : isWrong
                      ? "border-red-200 bg-red-50"
                      : "border-slate-200 bg-slate-50"
                  }`}
                >
                  <div className="mb-3 flex items-start gap-2">
                    <span className="text-sm font-semibold text-blue-600">
                      문제 {qIdx + 1}
                    </span>
                    {isGraded && (
                      <span
                        className={`flex items-center gap-1 text-xs font-medium ${
                          isCorrect ? "text-green-600" : "text-red-600"
                        }`}
                      >
                        {isCorrect ? (
                          <CheckCircle2 className="w-3 h-3" />
                        ) : (
                          <XCircle className="w-3 h-3" />
                        )}
                        {isCorrect ? "정답" : "오답"}
                      </span>
                    )}
                  </div>

                  <p className="mb-4 text-sm font-medium text-slate-900">
                    {question.question}
                  </p>

                  <div className="space-y-2">
                    {question.options.map((option, optIdx) => {
                      const isSelected =
                        userAnswer?.selectedOption === optIdx;
                      const isCorrectOption = optIdx === question.correct_answer;
                      const showCorrect =
                        isGraded && (isCorrectOption || (isSelected && isWrong));

                      return (
                        <button
                          key={optIdx}
                          onClick={() => handleAnswerSelect(question.id, optIdx)}
                          disabled={isGraded}
                          className={`w-full flex items-center rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                            isSelected
                              ? "border-blue-500 bg-blue-50 text-blue-900"
                              : "border-slate-300 bg-white text-slate-700 hover:border-slate-400"
                          } ${
                            showCorrect
                              ? "border-green-500 bg-green-50"
                              : ""
                          } ${
                            isGraded
                              ? "cursor-default"
                              : "cursor-pointer hover:bg-slate-50"
                          }`}
                        >
                          <span className="mr-2 font-medium">
                            {String.fromCharCode(65 + optIdx)}.
                          </span>
                          <span className="flex-1">{option}</span>
                          {showCorrect && (
                            <CheckCircle2 className="ml-2 w-4 h-4 text-green-600" />
                          )}
                        </button>
                      );
                    })}
                  </div>

                  {isGraded && question.explanation && (
                    <div className="mt-3 flex items-start gap-2 rounded-md bg-blue-50 border border-blue-200 px-3 py-2 text-xs text-slate-700">
                      <Lightbulb className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                      <span>{question.explanation}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {!quiz && !isLoading && !error && (
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-center text-sm text-slate-500">
            <p>퀴즈를 생성하려면 새로고침 버튼을 클릭하세요.</p>
            <button
              onClick={generateQuiz}
              className="mt-2 rounded-md bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-700 transition-colors"
            >
              퀴즈 생성
            </button>
          </div>
        )}
      </div>

      {/* 결과 표시 */}
      {result && isGraded && (
        <div className="border-t border-slate-200 bg-blue-50 px-4 py-4">
          <div className="mb-3 text-center">
            <div className="mb-1 flex items-center justify-center gap-2">
              <Trophy className="w-6 h-6 text-yellow-500" />
              <div className="text-2xl font-bold text-slate-900">
                {result.percentage}점
              </div>
            </div>
            <div className="text-sm text-slate-600">
              {result.score} / {result.total} 문제 정답
            </div>
            <div
              className={`mt-2 flex items-center justify-center gap-1 text-xs font-medium ${
                result.percentage >= 80
                  ? "text-green-600"
                  : result.percentage >= 60
                  ? "text-yellow-600"
                  : "text-red-600"
              }`}
            >
              {result.percentage >= 80
                ? "훌륭합니다!"
                : result.percentage >= 60
                ? "잘했어요!"
                : "다시 도전해보세요!"}
            </div>
          </div>
        </div>
      )}

      {/* 하단 버튼 */}
      <div className="border-t border-slate-200 bg-slate-50 px-4 py-3">
        <div className="flex gap-2">
          {!isGraded ? (
            <>
              <button
                onClick={handleSubmit}
                disabled={isSubmitting || !quiz || userAnswers.some((a) => a.selectedOption === null)}
                className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    채점 중...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    제출하기
                  </>
                )}
              </button>
              <button
                onClick={generateQuiz}
                disabled={isLoading}
                className="flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                새로고침
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleReset}
                className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                새 퀴즈 풀기
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

