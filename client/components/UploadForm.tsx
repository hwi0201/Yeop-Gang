"use client";

import { useState, useEffect, useRef } from "react";
import { Upload, FileVideo, FileAudio, FileText, X, CheckCircle2, AlertCircle } from "lucide-react";
import ProgressBar from "./ProgressBar";
import { API_BASE_URL, apiGet, apiUpload, handleApiError } from "../lib/api";

type Props = {
  instructorId?: string;
  parentCourseId?: string;  // 챕터 업로드 시 부모 강의 ID
  totalChapters?: number;  // 전체 강의 수 (챕터 업로드 시 표시용)
  onSubmitted?: (courseId: string) => void;
};

type StatusResponse = {
  course_id: string;
  status: string;
  progress: number;
  message?: string;
};

export default function UploadForm({ instructorId: propInstructorId, parentCourseId, totalChapters, onSubmitted }: Props) {
  const [instructorId, setInstructorId] = useState(propInstructorId || "");
  const [instructorName, setInstructorName] = useState("");
  const [courseId, setCourseId] = useState("");
  const [courseTitle, setCourseTitle] = useState("");
  const [courseCategory, setCourseCategory] = useState("");
  const [isChapter, setIsChapter] = useState(!!parentCourseId);
  const [parentCourseIdInput, setParentCourseIdInput] = useState(parentCourseId || "");
  const [chapterNumber, setChapterNumber] = useState<number | "">("");
  const [video, setVideo] = useState<File | null>(null);
  const [audio, setAudio] = useState<File | null>(null);
  const [pdf, setPdf] = useState<File | null>(null);
  const [smi, setSmi] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");
  const [progress, setProgress] = useState<number>(0);
  const [progressMessage, setProgressMessage] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // propInstructorId가 변경되면 업데이트
  useEffect(() => {
    if (propInstructorId) {
      setInstructorId(propInstructorId);
    }
  }, [propInstructorId]);

  // 챕터 번호가 변경되면 챕터 ID 자동 생성
  useEffect(() => {
    if (parentCourseId && chapterNumber !== "" && chapterNumber !== null && chapterNumber !== undefined) {
      setCourseId(`${parentCourseId}-${chapterNumber}`);
    }
  }, [parentCourseId, chapterNumber]);

  // 진행도 폴링 함수
  const pollStatus = async (currentCourseId: string) => {
    try {
      const data = await apiGet<StatusResponse>(`/api/status/${currentCourseId}`);
      setProgress(data.progress);
      
      if (data.status === "completed") {
        setIsProcessing(false);
        setStatus(`처리 완료! (${data.progress}%)`);
        setProgressMessage("처리 완료");
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        // 완료 후 약간의 지연을 두고 콜백 호출
        setTimeout(() => {
          onSubmitted?.(currentCourseId);
        }, 1000);
      } else if (data.status === "failed") {
        setIsProcessing(false);
        let errorMsg = data.message || "알 수 없는 오류가 발생했습니다. 백엔드 서버 로그를 확인하세요.";
        // "처리 실패:" 중복 제거
        if (errorMsg.startsWith("처리 실패:")) {
          errorMsg = errorMsg.replace("처리 실패:", "").trim();
        }
        setStatus(`처리 실패: ${errorMsg}`);
        setProgressMessage("처리 실패");
        setUploadError(errorMsg);
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      } else if (data.status === "processing") {
        // 처리 중인 상태이면 계속 폴링
        setStatus(`처리 중... (${data.progress}%)`);
        if (data.message) {
          setProgressMessage(data.message);
        }
      }
    } catch (err: any) {
      console.error("Status polling error:", err);
      // 429 에러인 경우 폴링 간격을 늘림
      if (err?.status === 429 || err?.response?.status === 429) {
        console.warn("Rate limit exceeded, increasing polling interval...");
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          // 폴링 간격을 5초로 늘림
          pollingIntervalRef.current = setInterval(() => {
            pollStatus(currentCourseId);
          }, 5000);
        }
      }
    }
  };

  // 컴포넌트 언마운트 시 폴링 정리
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const handleSubmit = async () => {
    if (!instructorId || !courseId) {
      setStatus("instructorId와 courseId를 입력하세요.");
      setUploadError(null);
      return;
    }

    if (!courseTitle || !courseTitle.trim()) {
      setStatus(`${parentCourseId ? "챕터명" : "강의명"}을 입력하세요.`);
      setUploadError(null);
      return;
    }
    
    // 에러 상태 초기화
    setUploadError(null);
    
    const form = new FormData();
    form.append("instructor_id", instructorId);
    form.append("course_id", courseId);
    if (instructorName.trim()) form.append("instructor_name", instructorName.trim());
    form.append("course_title", courseTitle.trim()); // 필수 항목
    if (courseCategory.trim()) form.append("course_category", courseCategory.trim());
    const finalParentCourseId = parentCourseId || parentCourseIdInput;
    if (isChapter && finalParentCourseId.trim()) {
      form.append("parent_course_id", finalParentCourseId.trim());
      if (chapterNumber !== "") {
        form.append("chapter_number", String(chapterNumber));
      }
    }
    if (video) form.append("video", video);
    if (audio) form.append("audio", audio);
    if (pdf) form.append("pdf", pdf);
    if (smi) form.append("smi", smi);

    setStatus("파일 업로드 중...");
    setProgress(0);
    setProgressMessage("업로드 중...");
    setIsProcessing(true);

    try {
      // 강사 토큰 가져오기
      const token = typeof window !== "undefined" ? localStorage.getItem("instructor_token") : null;
      
      const options: RequestInit = {};
      if (token) {
        options.headers = {
          Authorization: `Bearer ${token}`,
        };
      }

      const json = await apiUpload<{ course_id: string; instructor_id: string; status: string }>(
        "/api/instructor/upload",
        form,
        options
      );
      setStatus("업로드 완료. 처리 시작 중...");
      setProgress(5);
      setProgressMessage("업로드 완료, 처리 대기 중...");

      // 업로드 성공 후 진행도 폴링 시작 (2초마다 확인)
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
      
      // 즉시 한 번 확인
      pollStatus(courseId);
      
      // 그 다음부터는 3초마다 확인 (rate limit 방지)
      pollingIntervalRef.current = setInterval(() => {
        pollStatus(courseId);
      }, 3000);
    } catch (err) {
      console.error("업로드 오류:", err);
      
      const apiError = handleApiError(err);
      const errorMessage = apiError.message;
      
      setUploadError(errorMessage);
      setStatus(`업로드 실패: ${errorMessage}`);
      setProgress(0);
      setProgressMessage("");
      setIsProcessing(false);
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
  };

  return (
    <div className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-lg">
      {/* 기본 정보 입력 */}
      <div className="space-y-4">
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-700">
            강사 ID
          </label>
          <input
            className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition-colors focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 disabled:bg-slate-50 disabled:text-slate-500"
            placeholder="강사 식별자를 입력하세요"
            value={instructorId}
            onChange={(e) => setInstructorId(e.target.value)}
            disabled={isProcessing || !!propInstructorId}
          />
          {propInstructorId && (
            <p className="mt-1 text-xs text-slate-500">
              로그인된 강사 ID가 자동으로 입력되었습니다.
            </p>
          )}
        </div>
        {/* 챕터 ID - parentCourseId가 있으면 자동 생성, 없으면 수동 입력 */}
        {parentCourseId ? (
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">
              챕터 ID (자동 생성)
            </label>
            <input
              className="w-full rounded-lg border border-slate-300 bg-slate-50 px-4 py-2.5 text-sm text-slate-500 outline-none"
              value={chapterNumber !== "" ? `${parentCourseId}-${chapterNumber}` : `${parentCourseId}-{번호}`}
              disabled
              readOnly
            />
            <p className="mt-1 text-xs text-slate-500">
              챕터 번호를 입력하면 자동으로 생성됩니다.
            </p>
          </div>
        ) : (
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">
              강의 ID <span className="text-red-500">*</span>
            </label>
            <input
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition-colors focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              placeholder="강의 식별자를 입력하세요"
              value={courseId}
              onChange={(e) => setCourseId(e.target.value)}
              disabled={isProcessing}
            />
          </div>
        )}
        {/* 강사명 - 챕터 업로드 시에는 부모 강의의 강사명을 사용하므로 숨김 */}
        {!parentCourseId && (
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">
              강사명 (선택사항)
            </label>
            <input
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition-colors focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              placeholder="예: 조은희 선생님"
              value={instructorName}
              onChange={(e) => setInstructorName(e.target.value)}
              disabled={isProcessing}
            />
            <p className="mt-1 text-xs text-slate-500">
              강사명을 입력하면 학생 페이지에서 표시됩니다.
            </p>
          </div>
        )}
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-700">
            {parentCourseId ? "챕터명" : "강의명"} <span className="text-red-500">*</span>
          </label>
          <input
            className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition-colors focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
            placeholder={parentCourseId ? "예: 1강 - 세포의 구조" : "예: 실전모의고사 1회차 (10강)"}
            value={courseTitle}
            onChange={(e) => setCourseTitle(e.target.value)}
            disabled={isProcessing}
            required
          />
          <p className="mt-1 text-xs text-slate-500">
            {parentCourseId 
              ? "챕터명은 필수 입력 항목입니다."
              : "강의명은 필수 입력 항목입니다."}
          </p>
        </div>
        {/* 카테고리 - 챕터 업로드 시에는 부모 강의의 카테고리를 사용하므로 숨김 */}
        {!parentCourseId && (
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">
              카테고리 (선택사항)
            </label>
            <input
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition-colors focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              placeholder="예: 수능특강, 개념강의, 실전모의고사"
              value={courseCategory}
              onChange={(e) => setCourseCategory(e.target.value)}
              disabled={isProcessing}
            />
            <p className="mt-1 text-xs text-slate-500">
              카테고리를 입력하면 검색 및 필터링에 사용됩니다.
            </p>
          </div>
        )}

        {/* 챕터 옵션 - parentCourseId가 없을 때만 표시 (일반 강의 업로드 시) */}
        {!parentCourseId && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isChapter}
                onChange={(e) => {
                  setIsChapter(e.target.checked);
                  if (!e.target.checked) {
                    setParentCourseIdInput("");
                    setChapterNumber("");
                  }
                }}
                disabled={isProcessing}
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-2 focus:ring-blue-500/20"
              />
              <span className="text-sm font-medium text-slate-700">
                챕터로 등록하기
              </span>
            </label>
            <p className="mt-1 text-xs text-slate-500">
              체크하면 이 강의를 다른 강의의 챕터로 등록할 수 있습니다.
            </p>
            
            {isChapter && (
              <div className="mt-4 space-y-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700">
                    부모 강의 ID <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={parentCourseIdInput}
                    onChange={(e) => setParentCourseIdInput(e.target.value)}
                    placeholder="예: 생명과학1개념강의"
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition-colors focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                    disabled={isProcessing}
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    이 챕터가 속할 메인 강의의 ID를 입력하세요.
                  </p>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700">
                    챕터 번호 (선택사항)
                  </label>
                  <input
                    type="number"
                    value={chapterNumber}
                    onChange={(e) => {
                      const val = e.target.value;
                      setChapterNumber(val === "" ? "" : parseInt(val, 10));
                    }}
                    placeholder="예: 1, 2, 3..."
                    min="1"
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition-colors focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                    disabled={isProcessing}
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    챕터 순서를 지정합니다. (1, 2, 3...)
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* 챕터 업로드 시 전체 강의 수 및 챕터 번호 표시 */}
        {parentCourseId && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-4">
            {totalChapters !== undefined && totalChapters !== null && (
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  전체 강의 수
                </label>
                <input
                  type="number"
                  value={totalChapters}
                  className="w-full rounded-lg border border-slate-300 bg-slate-100 px-3 py-2 text-sm text-slate-600 outline-none"
                  disabled
                  readOnly
                />
                <p className="mt-1 text-xs text-slate-500">
                  강의 목록 생성 시 설정한 전체 강의 수입니다.
                </p>
              </div>
            )}
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                현재 업로드할 강의 번호 <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                value={chapterNumber}
                onChange={(e) => {
                  const val = e.target.value;
                  const num = val === "" ? "" : parseInt(val, 10);
                  setChapterNumber(num);
                  // 챕터 ID 자동 생성
                  if (num !== "" && parentCourseId) {
                    setCourseId(`${parentCourseId}-${num}`);
                  }
                }}
                placeholder="예: 1, 2, 3..."
                min="1"
                max={totalChapters || undefined}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition-colors focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                disabled={isProcessing}
                required
              />
              <p className="mt-1 text-xs text-slate-500">
                현재 업로드할 강의의 번호를 입력하세요. (1, 2, 3...)
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 파일 업로드 섹션 */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-900">파일 업로드</h3>
        
        {/* 비디오 업로드 */}
        <label className="block">
          <div className="flex cursor-pointer items-center gap-3 rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-4 transition-colors hover:border-blue-400 hover:bg-blue-50/50">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
              <FileVideo className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-slate-700">
                {video ? video.name : "비디오 파일 (MP4, AVI, MOV 등)"}
              </div>
              {video && (
                <div className="mt-1 text-xs text-slate-500">
                  {formatFileSize(video.size)}
                </div>
              )}
            </div>
            {video && (
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setVideo(null);
                }}
                className="rounded-full p-1 text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          <input
            type="file"
            accept="video/*,.mp4,.avi,.mov,.mkv,.webm"
            className="hidden"
            onChange={(e) => setVideo(e.target.files?.[0] ?? null)}
            disabled={isProcessing}
          />
        </label>

        {/* 오디오 업로드 */}
        <label className="block">
          <div className="flex cursor-pointer items-center gap-3 rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-4 transition-colors hover:border-blue-400 hover:bg-blue-50/50">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 text-green-600">
              <FileAudio className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-slate-700">
                {audio ? audio.name : "오디오 파일 (MP3, WAV, M4A 등)"}
              </div>
              {audio && (
                <div className="mt-1 text-xs text-slate-500">
                  {formatFileSize(audio.size)}
                </div>
              )}
            </div>
            {audio && (
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setAudio(null);
                }}
                className="rounded-full p-1 text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          <input
            type="file"
            accept="audio/*,.mp3,.wav,.m4a,.aac,.ogg,.flac"
            className="hidden"
            onChange={(e) => setAudio(e.target.files?.[0] ?? null)}
            disabled={isProcessing}
          />
        </label>

        {/* PDF 업로드 */}
        <label className="block">
          <div className="flex cursor-pointer items-center gap-3 rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-4 transition-colors hover:border-blue-400 hover:bg-blue-50/50">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 text-purple-600">
              <FileText className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-slate-700">
                {pdf ? pdf.name : "PDF 파일 (선택사항)"}
              </div>
              {pdf && (
                <div className="mt-1 text-xs text-slate-500">
                  {formatFileSize(pdf.size)}
                </div>
              )}
            </div>
            {pdf && (
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setPdf(null);
                }}
                className="rounded-full p-1 text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          <input
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => setPdf(e.target.files?.[0] ?? null)}
            disabled={isProcessing}
          />
        </label>

        {/* SMI 자막 파일 업로드 */}
        <label className="block">
          <div className="flex cursor-pointer items-center gap-3 rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-4 transition-colors hover:border-blue-400 hover:bg-blue-50/50">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
              <FileText className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-slate-700">
                {smi ? smi.name : "SMI 자막 파일 (선택사항, STT 대체)"}
              </div>
              {smi && (
                <div className="mt-1 text-xs text-slate-500">
                  {formatFileSize(smi.size)}
                </div>
              )}
              {!smi && (
                <div className="mt-1 text-xs text-slate-500">
                  SMI 파일이 있으면 STT를 건너뛰고 자막을 사용합니다
                </div>
              )}
            </div>
            {smi && (
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setSmi(null);
                }}
                className="rounded-full p-1 text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          <input
            type="file"
            accept=".smi,.sami"
            className="hidden"
            onChange={(e) => setSmi(e.target.files?.[0] ?? null)}
            disabled={isProcessing}
          />
        </label>
      </div>

      {/* 업로드 버튼 */}
      <button
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-all hover:bg-blue-700 hover:shadow-md disabled:bg-slate-400 disabled:cursor-not-allowed"
        onClick={handleSubmit}
        disabled={isProcessing || !instructorId || !courseId || !courseTitle || !courseTitle.trim()}
      >
        {isProcessing ? (
          <>
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            <span>처리 중...</span>
          </>
        ) : (
          <>
            <Upload className="h-4 w-4" />
            <span>업로드 시작</span>
          </>
        )}
      </button>
      
      {/* 진행도 바 표시 */}
      {isProcessing && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <ProgressBar progress={progress} message={progressMessage} />
        </div>
      )}
      
      {status && (
        <div
          className={`flex items-start gap-3 rounded-lg px-4 py-3 text-sm ${
            status.includes("완료") && !isProcessing
              ? "bg-green-50 text-green-700 border border-green-200"
              : status.includes("실패") || status.includes("오류")
              ? "bg-red-50 text-red-700 border border-red-200"
              : "bg-blue-50 text-blue-700 border border-blue-200"
          }`}
        >
          {status.includes("완료") && !isProcessing ? (
            <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
          ) : status.includes("실패") || status.includes("오류") ? (
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
          ) : null}
          <div className="flex-1">
            <div className="font-medium">{status}</div>
            {uploadError && !isProcessing && (
              <button
                onClick={handleSubmit}
                className="mt-2 rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-red-700"
              >
                다시 시도
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
