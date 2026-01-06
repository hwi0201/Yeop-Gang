/**
 * API 공통 유틸리티
 * - API 기본 URL 관리
 * - 공통 fetch 함수
 * - 에러 처리
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type ApiError = {
  message: string;
  status?: number;
  code?: string;
};

/**
 * 공통 API 에러 처리
 */
export function handleApiError(error: unknown): ApiError {
  // 네트워크 오류
  if (error instanceof TypeError && error.message.includes("fetch")) {
    return {
      message: "네트워크 연결을 확인할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.",
      code: "NETWORK_ERROR",
    };
  }

  // 일반 Error 객체
  if (error instanceof Error) {
    return {
      message: error.message,
    };
  }

  // 알 수 없는 오류
  return {
    message: "알 수 없는 오류가 발생했습니다.",
    code: "UNKNOWN_ERROR",
  };
}

/**
 * HTTP 상태 코드에 따른 에러 메시지 생성
 */
export function getHttpErrorMessage(status: number): string {
  switch (status) {
    case 400:
      return "잘못된 요청입니다. 입력값을 확인해주세요.";
    case 401:
      return "인증이 필요합니다.";
    case 403:
      return "접근 권한이 없습니다.";
    case 404:
      return "요청한 리소스를 찾을 수 없습니다.";
    case 413:
      return "파일 크기가 너무 큽니다.";
    case 429:
      return "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.";
    case 500:
      return "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
    case 503:
      return "서버가 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요.";
    default:
      return `서버 오류 (${status})`;
  }
}

/**
 * 공통 fetch 래퍼 함수
 */
export async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorMessage = getHttpErrorMessage(response.status);
      throw new Error(errorMessage);
    }

    // 빈 응답 처리
    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      return {} as T;
    }

    return await response.json();
  } catch (error) {
    throw handleApiError(error);
  }
}

/**
 * POST 요청 헬퍼
 */
export async function apiPost<T>(
  endpoint: string,
  data?: unknown,
  options?: RequestInit
): Promise<T> {
  return apiFetch<T>(endpoint, {
    method: "POST",
    body: data ? JSON.stringify(data) : undefined,
    ...options,
  });
}

/**
 * GET 요청 헬퍼
 */
export async function apiGet<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  return apiFetch<T>(endpoint, {
    method: "GET",
    ...options,
  });
}

/**
 * DELETE 요청 헬퍼
 */
export async function apiDelete<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  return apiFetch<T>(endpoint, {
    method: "DELETE",
    ...options,
  });
}

/**
 * 파일 업로드용 POST 요청
 */
export async function apiUpload<T>(
  endpoint: string,
  formData: FormData,
  options?: RequestInit
): Promise<T> {
  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      method: "POST",
      body: formData,
      ...options,
    });

    if (!response.ok) {
      const errorMessage = getHttpErrorMessage(response.status);
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (error) {
    throw handleApiError(error);
  }
}

