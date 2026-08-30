import { useMutation } from '@tanstack/react-query';

import { deleteMedia, uploadMedia } from '@/api/media';
import { ApiError } from '@/api/errors';
import type { MediaKind } from '@/schemas';
import { toastError } from '@/store/toastStore';

export function useUploadMedia() {
  return useMutation({
    mutationFn: ({ file, kind }: { file: File; kind: MediaKind }) => uploadMedia(file, kind),
    onError: (error) => {
      toastError(error instanceof ApiError ? error.detail : 'Failed to upload media');
    },
  });
}

export function useDeleteMedia() {
  return useMutation({
    mutationFn: (id: number) => deleteMedia(id),
    onError: (error) => {
      toastError(error instanceof ApiError ? error.detail : 'Failed to delete media');
    },
  });
}
