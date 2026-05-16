import { ApiErrorBody } from '@/schemas';

/**
 * Thrown for any failed REST call: non-2xx response, network error, or a
 * response whose body fails zod validation against the endpoint's response
 * schema. Components surface ApiError.detail via toast.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly detail: string;

  constructor(args: { status: number; code: string; detail: string }) {
    super(args.detail);
    this.name = 'ApiError';
    this.status = args.status;
    this.code = args.code;
    this.detail = args.detail;
  }

  static async fromResponse(res: Response): Promise<ApiError> {
    let detail = `Request failed with status ${res.status}`;
    try {
      const json = (await res.json()) as unknown;
      const parsed = ApiErrorBody.safeParse(json);
      if (parsed.success) {
        const d = parsed.data.detail;
        if (typeof d === 'string') detail = d;
        else detail = JSON.stringify(d);
      }
    } catch {
      // body wasn't JSON; keep generic detail
    }
    return new ApiError({ status: res.status, code: codeForStatus(res.status), detail });
  }
}

function codeForStatus(status: number): string {
  if (status === 401) return 'unauthorized';
  if (status === 403) return 'forbidden';
  if (status === 404) return 'not_found';
  if (status === 409) return 'conflict';
  if (status === 422) return 'validation';
  if (status >= 500) return 'server_error';
  return 'http_error';
}
