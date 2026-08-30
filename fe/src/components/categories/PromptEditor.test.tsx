import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { MediaAsset, PromptInDB } from '@/schemas';
import PromptEditor from './PromptEditor';

const uploadMedia = vi.hoisted(() => vi.fn());
const deleteMedia = vi.hoisted(() => vi.fn());
const createPrompt = vi.hoisted(() => vi.fn());
const updatePrompt = vi.hoisted(() => vi.fn());
const getCategory = vi.hoisted(() => vi.fn());

vi.mock('@/api/media', () => ({ uploadMedia, deleteMedia }));
vi.mock('@/api/categories', () => ({ getCategory }));
vi.mock('@/hooks/usePromptCategories', () => ({
  useCreatePrompt: () => ({ mutateAsync: createPrompt, isPending: false }),
  useUpdatePrompt: () => ({ mutateAsync: updatePrompt, isPending: false }),
  useDeletePrompt: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

const questionAsset: MediaAsset = {
  id: 1,
  owner_id: 1,
  storage_key: 'a'.repeat(32) + '.png',
  original_filename: 'question.png',
  media_kind: 'image',
  mime_type: 'image/png',
  byte_size: 4,
  duration_seconds: null,
  width: null,
  height: null,
  created_at: '2026-08-30T00:00:00Z',
  url: '/media/' + 'a'.repeat(32) + '.png',
};

const answerAsset: MediaAsset = {
  ...questionAsset,
  id: 2,
  storage_key: 'b'.repeat(32) + '.png',
  original_filename: 'answer.png',
  url: '/media/' + 'b'.repeat(32) + '.png',
};

const existingPrompt: PromptInDB = {
  id: 11,
  question: 'Name this color',
  question_type: 'image',
  question_media_asset_id: questionAsset.id,
  answer: 'Blue',
  answer_type: 'image',
  answer_media_asset_id: answerAsset.id,
  category_id: 9,
  order: 1,
  question_content: {
    type: 'image',
    text: 'Name this color',
    media: {
      asset_id: questionAsset.id,
      url: questionAsset.url,
      mime_type: questionAsset.mime_type,
      filename: questionAsset.original_filename,
    },
  },
  answer_content: {
    type: 'image',
    text: 'Blue',
    media: {
      asset_id: answerAsset.id,
      url: answerAsset.url,
      mime_type: answerAsset.mime_type,
      filename: answerAsset.original_filename,
    },
  },
};

function renderEditor(existing: PromptInDB | null = existingPrompt) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <PromptEditor categoryId={9} order={1} existing={existing ?? undefined} />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe('PromptEditor media controls', () => {
  it('renders persisted previews and accessible in-preview removal controls', () => {
    renderEditor();

    expect(screen.getByAltText('Question media preview')).toHaveAttribute('src', questionAsset.url);
    expect(screen.getByAltText('Answer reveal media preview')).toHaveAttribute(
      'src',
      answerAsset.url,
    );
    expect(screen.getByRole('button', { name: 'Remove question media' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Remove answer media' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Upload media' })).not.toBeInTheDocument();
  });

  it('previews and uploads valid media immediately, then revokes local URL', async () => {
    const user = userEvent.setup();
    const localUrl = 'blob:question-preview';
    const revokeObjectUrl = vi.fn();
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => localUrl),
      revokeObjectURL: revokeObjectUrl,
    });
    let finishUpload: (asset: MediaAsset) => void;
    uploadMedia.mockImplementation(
      () =>
        new Promise<MediaAsset>((resolve) => {
          finishUpload = resolve;
        }),
    );
    renderEditor();

    const inputs = document.querySelectorAll<HTMLInputElement>('input[type="file"]');
    const file = new File(['image'], 'new-question.png', { type: 'image/png' });
    await user.upload(inputs[0], file);

    expect(uploadMedia).toHaveBeenCalledWith(file, 'image');
    expect(screen.getByAltText('Question media preview')).toHaveAttribute('src', localUrl);
    expect(screen.getAllByText('Uploading…')).not.toHaveLength(0);
    expect(screen.getByRole('button', { name: 'Remove question media' })).toBeDisabled();

    finishUpload!({ ...questionAsset, id: 3, url: '/media/new-question.png' });
    await waitFor(() =>
      expect(screen.getByAltText('Question media preview')).toHaveAttribute(
        'src',
        '/media/new-question.png',
      ),
    );
    expect(revokeObjectUrl).toHaveBeenCalledWith(localUrl);
  });

  it('retains persisted media after failed replacement', async () => {
    const user = userEvent.setup();
    const localUrl = 'blob:failed-question-preview';
    const revokeObjectUrl = vi.fn();
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => localUrl),
      revokeObjectURL: revokeObjectUrl,
    });
    uploadMedia.mockRejectedValue(new Error('upload failed'));
    renderEditor();

    const inputs = document.querySelectorAll<HTMLInputElement>('input[type="file"]');
    await user.upload(inputs[0], new File(['image'], 'bad.png', { type: 'image/png' }));

    await waitFor(() => expect(screen.getByText('Upload failed')).toBeInTheDocument());
    expect(screen.getByAltText('Question media preview')).toHaveAttribute('src', questionAsset.url);
    expect(revokeObjectUrl).toHaveBeenCalledWith(localUrl);
  });

  it('restores persisted media and cleans replacement upload after prompt save failure', async () => {
    const user = userEvent.setup();
    const localUrl = 'blob:save-failed-question-preview';
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => localUrl), revokeObjectURL: vi.fn() });
    uploadMedia.mockResolvedValue({
      ...questionAsset,
      id: 8,
      url: '/media/replacement-question.png',
    });
    updatePrompt.mockRejectedValue(new Error('save failed'));
    deleteMedia.mockResolvedValue(undefined);
    renderEditor();

    const inputs = document.querySelectorAll<HTMLInputElement>('input[type="file"]');
    await user.upload(inputs[0], new File(['image'], 'replacement.png', { type: 'image/png' }));
    await waitFor(() =>
      expect(screen.getByAltText('Question media preview')).toHaveAttribute(
        'src',
        '/media/replacement-question.png',
      ),
    );
    await user.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() =>
      expect(screen.getByAltText('Question media preview')).toHaveAttribute(
        'src',
        questionAsset.url,
      ),
    );
    expect(deleteMedia).toHaveBeenCalledWith(8);
  });

  it('removes unassigned uploaded media, resets type to text, and cleans it up', async () => {
    const user = userEvent.setup();
    const localUrl = 'blob:new-question-preview';
    const revokeObjectUrl = vi.fn();
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => localUrl),
      revokeObjectURL: revokeObjectUrl,
    });
    uploadMedia.mockResolvedValue({ ...questionAsset, id: 7, url: '/media/new-question.png' });
    deleteMedia.mockResolvedValue(undefined);
    renderEditor(null);

    const questionType = screen.getByLabelText('Question type');
    await user.selectOptions(questionType, 'image');
    const inputs = document.querySelectorAll<HTMLInputElement>('input[type="file"]');
    await user.upload(inputs[0], new File(['image'], 'new-question.png', { type: 'image/png' }));
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Remove question media' })).toBeEnabled(),
    );

    await user.click(screen.getByRole('button', { name: 'Remove question media' }));

    expect(questionType).toHaveValue('text');
    expect(deleteMedia).toHaveBeenCalledWith(7);
    expect(revokeObjectUrl).toHaveBeenCalledWith(localUrl);
  });

  it('revokes local object URLs when editor unmounts', async () => {
    const user = userEvent.setup();
    const localUrl = 'blob:unmount-preview';
    const revokeObjectUrl = vi.fn();
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => localUrl),
      revokeObjectURL: revokeObjectUrl,
    });
    uploadMedia.mockImplementation(() => new Promise<MediaAsset>(() => undefined));
    const view = renderEditor();

    const inputs = document.querySelectorAll<HTMLInputElement>('input[type="file"]');
    await user.upload(inputs[0], new File(['image'], 'new-question.png', { type: 'image/png' }));
    view.unmount();

    expect(revokeObjectUrl).toHaveBeenCalledWith(localUrl);
  });
});
