/** 用户可见的统一网络错误文案 */
export const NETWORK_ERROR = 'network error';

export function asNetworkError(): Error {
  return new Error(NETWORK_ERROR);
}

/** 任意 fetch / API 失败统一映射为 network error */
export function toNetworkError(_err?: unknown): Error {
  return asNetworkError();
}
