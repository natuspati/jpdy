import { useCallback, useEffect, useRef, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient } from '@tanstack/react-query';

import { getCategory } from '@/api/categories';
import { deleteMedia } from '@/api/media';
import { queryKeys } from '@/api/queryKeys';
import PromptMedia from '@/components/game/PromptMedia';
import Button from '@/components/ui/Button';
import Field from '@/components/ui/Field';
import HelpTip from '@/components/ui/HelpTip';
import Input from '@/components/ui/Input';
import { useUploadMedia } from '@/hooks/useMedia';
import { useCreatePrompt, useDeletePrompt, useUpdatePrompt } from '@/hooks/usePromptCategories';
import {
  PromptCreate,
  type MediaAsset,
  type MediaKind,
  type MediaReference,
  type PromptContentType,
  type PromptInDB,
} from '@/schemas';
import { toastError } from '@/store/toastStore';

type SlotName = 'question' | 'answer';

type SlotValues = {
  question: string;
  question_type: PromptContentType;
  question_media_asset_id: number | null;
  answer: string;
  answer_type: PromptContentType;
  answer_media_asset_id: number | null;
  order: number;
};

interface Props {
  categoryId: number;
  order: number;
  existing: PromptInDB | undefined;
}

interface MediaControlProps {
  slot: SlotName;
  contentType: PromptContentType;
  media: MediaReference | null;
  unassignedAssetId: number | null;
  disabled: boolean;
  onUploaded: (asset: MediaAsset) => void;
  onRemove: () => Promise<void>;
  onUploadStateChange: (pending: boolean) => void;
}

interface PersistedSlot {
  type: PromptContentType;
  media: MediaReference | null;
  assetId: number | null;
}

const fileRules: Record<
  MediaKind,
  {
    accept: string;
    maxBytes: number;
    guidance: string;
    mimeTypes: readonly string[];
    extensions: readonly string[];
  }
> = {
  image: {
    accept: 'image/jpeg,image/png,image/webp',
    maxBytes: 10 * 1024 * 1024,
    guidance: 'JPEG, PNG, or WebP. Max 10 MB.',
    mimeTypes: ['image/jpeg', 'image/png', 'image/webp'],
    extensions: ['.jpg', '.jpeg', '.png', '.webp'],
  },
  audio: {
    accept: 'audio/mpeg,audio/mp4,audio/aac,audio/ogg,.mp3,.m4a,.aac,.ogg',
    maxBytes: 20 * 1024 * 1024,
    guidance: 'MP3, M4A/AAC, or Ogg. Max 20 MB.',
    mimeTypes: ['audio/mpeg', 'audio/mp4', 'audio/aac', 'audio/ogg'],
    extensions: ['.mp3', '.m4a', '.aac', '.ogg'],
  },
  video: {
    accept: 'video/mp4,.mp4',
    maxBytes: 100 * 1024 * 1024,
    guidance: 'MP4 (H.264/AAC). Max 100 MB.',
    mimeTypes: ['video/mp4'],
    extensions: ['.mp4'],
  },
};

const contentTypeOptions = ['text', 'image', 'audio', 'video'] as const;

const asReference = (asset: MediaAsset): MediaReference => ({
  asset_id: asset.id,
  url: asset.url,
  mime_type: asset.mime_type,
  filename: asset.original_filename,
});

const mediaKindFor = (contentType: PromptContentType): MediaKind | null =>
  contentType === 'text' ? null : contentType;

const getSlot = (prompt: PromptInDB | undefined, slot: SlotName): PersistedSlot =>
  slot === 'question'
    ? {
        type: prompt?.question_type ?? 'text',
        media: prompt?.question_content.media ?? null,
        assetId: prompt?.question_media_asset_id ?? null,
      }
    : {
        type: prompt?.answer_type ?? 'text',
        media: prompt?.answer_content.media ?? null,
        assetId: prompt?.answer_media_asset_id ?? null,
      };

const isAllowedFile = (file: File, rules: (typeof fileRules)[MediaKind]): boolean => {
  const name = file.name.toLowerCase();
  return (
    rules.mimeTypes.includes(file.type) ||
    rules.extensions.some((extension) => name.endsWith(extension))
  );
};

const MediaControl = ({
  slot,
  contentType,
  media,
  unassignedAssetId,
  disabled,
  onUploaded,
  onRemove,
  onUploadStateChange,
}: MediaControlProps) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const localUrlRef = useRef<string | null>(null);
  const [localUrl, setLocalUrl] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'uploading' | 'failed'>('idle');
  const [removing, setRemoving] = useState(false);
  const upload = useUploadMedia();
  const kind = mediaKindFor(contentType);

  const revokeLocalUrl = () => {
    if (localUrlRef.current) {
      URL.revokeObjectURL(localUrlRef.current);
      localUrlRef.current = null;
    }
    setLocalUrl(null);
  };

  useEffect(
    () => () => {
      if (localUrlRef.current) URL.revokeObjectURL(localUrlRef.current);
    },
    [],
  );

  useEffect(() => {
    onUploadStateChange(status === 'uploading');
  }, [onUploadStateChange, status]);

  if (!kind) return null;

  const rules = fileRules[kind];
  const label = slot === 'question' ? 'Question' : 'Answer reveal';
  const slotLabel = slot === 'question' ? 'question' : 'answer';
  const hasPreview = localUrl !== null || media !== null;
  const blocked = disabled || status === 'uploading' || removing;

  const handleSelection = async (file: File | undefined) => {
    if (inputRef.current) inputRef.current.value = '';
    if (!file) return;
    if (!isAllowedFile(file, rules)) {
      toastError(`${label} file must be ${rules.guidance.toLowerCase()}`);
      return;
    }
    if (file.size > rules.maxBytes) {
      toastError(`${label} file exceeds ${rules.maxBytes / (1024 * 1024)} MB limit`);
      return;
    }

    revokeLocalUrl();
    const objectUrl = URL.createObjectURL(file);
    localUrlRef.current = objectUrl;
    setLocalUrl(objectUrl);
    setFilename(file.name);
    setStatus('uploading');
    try {
      const asset = await upload.mutateAsync({ file, kind });
      onUploaded(asset);
      revokeLocalUrl();
      setFilename(asset.original_filename);
      setStatus('idle');
    } catch {
      revokeLocalUrl();
      setStatus('failed');
    }
  };

  const handleRemove = async () => {
    setRemoving(true);
    try {
      await onRemove();
      revokeLocalUrl();
      setFilename(null);
      setStatus('idle');
    } finally {
      setRemoving(false);
    }
  };

  return (
    <div className="space-y-2 rounded border border-slate-700 bg-slate-950/30 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <p className="text-sm font-medium text-slate-200">{label} media</p>
          <HelpTip text={rules.guidance} />
        </div>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={blocked}
          onClick={() => inputRef.current?.click()}
        >
          {status === 'uploading'
            ? 'Uploading…'
            : hasPreview
              ? `Replace ${slotLabel} ${kind}`
              : `Select ${slotLabel} ${kind}`}
        </Button>
      </div>
      <input
        ref={inputRef}
        className="sr-only"
        type="file"
        accept={rules.accept}
        disabled={blocked}
        onChange={(event) => void handleSelection(event.target.files?.[0])}
      />
      {hasPreview ? (
        <div className="relative">
          <PromptMedia
            contentType={contentType}
            media={media}
            src={localUrl}
            alt={`${label} media preview`}
          />
          <button
            type="button"
            aria-label={`Remove ${slotLabel} media`}
            title={`Remove ${slotLabel} media`}
            disabled={blocked}
            onClick={() => void handleRemove()}
            className="absolute right-2 top-2 inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-950/85 text-xl leading-none text-white shadow hover:bg-rose-700 focus:outline-none focus:ring-2 focus:ring-amber-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span aria-hidden="true">×</span>
          </button>
        </div>
      ) : null}
      {filename ? <p className="text-xs text-slate-300">{filename}</p> : null}
      {status === 'uploading' ? (
        <p className="text-xs text-amber-300" role="status">
          Uploading…
        </p>
      ) : null}
      {status === 'failed' ? (
        <p className="text-xs text-rose-300" role="alert">
          Upload failed
        </p>
      ) : null}
      {unassignedAssetId !== null ? (
        <p className="text-xs text-slate-500">Upload will attach when prompt is saved.</p>
      ) : null}
    </div>
  );
};

const toValues = (prompt: PromptInDB): SlotValues => ({
  question: prompt.question,
  question_type: prompt.question_type,
  question_media_asset_id: prompt.question_media_asset_id,
  answer: prompt.answer,
  answer_type: prompt.answer_type,
  answer_media_asset_id: prompt.answer_media_asset_id,
  order: prompt.order ?? 1,
});

const PromptEditor = ({ categoryId, order, existing }: Props) => {
  const queryClient = useQueryClient();
  const create = useCreatePrompt(categoryId);
  const update = useUpdatePrompt(categoryId);
  const remove = useDeletePrompt(categoryId);
  const [questionMedia, setQuestionMedia] = useState<MediaReference | null>(
    existing?.question_content.media ?? null,
  );
  const [answerMedia, setAnswerMedia] = useState<MediaReference | null>(
    existing?.answer_content.media ?? null,
  );
  const [questionUnassignedId, setQuestionUnassignedId] = useState<number | null>(null);
  const [answerUnassignedId, setAnswerUnassignedId] = useState<number | null>(null);
  const [questionUploading, setQuestionUploading] = useState(false);
  const [answerUploading, setAnswerUploading] = useState(false);
  const [questionRemoval, setQuestionRemoval] = useState<PersistedSlot | null>(null);
  const [answerRemoval, setAnswerRemoval] = useState<PersistedSlot | null>(null);
  const [localMediaChange, setLocalMediaChange] = useState(false);
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isDirty },
    reset,
    control,
  } = useForm<SlotValues>({
    resolver: zodResolver(PromptCreate),
    defaultValues: {
      question: existing?.question ?? '',
      question_type: existing?.question_type ?? 'text',
      question_media_asset_id: existing?.question_media_asset_id ?? null,
      answer: existing?.answer ?? '',
      answer_type: existing?.answer_type ?? 'text',
      answer_media_asset_id: existing?.answer_media_asset_id ?? null,
      order,
    },
  });
  const questionType = useWatch({ control, name: 'question_type' });
  const answerType = useWatch({ control, name: 'answer_type' });

  const syncFromPrompt = useCallback(
    (prompt: PromptInDB) => {
      setQuestionMedia(prompt.question_content.media);
      setAnswerMedia(prompt.answer_content.media);
      setQuestionUnassignedId(null);
      setAnswerUnassignedId(null);
      setQuestionRemoval(null);
      setAnswerRemoval(null);
      setLocalMediaChange(false);
      reset(toValues(prompt));
    },
    [reset],
  );

  useEffect(() => {
    if (
      existing &&
      !localMediaChange &&
      !questionUploading &&
      !answerUploading &&
      questionRemoval === null &&
      answerRemoval === null
    ) {
      syncFromPrompt(existing);
    }
  }, [
    answerRemoval,
    answerUploading,
    existing,
    localMediaChange,
    questionRemoval,
    questionUploading,
    syncFromPrompt,
  ]);

  const cleanupAsset = async (assetId: number | null) => {
    if (assetId === null) return;
    try {
      await deleteMedia(assetId);
    } catch {
      toastError('Could not clean up unassigned media');
    }
  };

  const removeSlot = async (slot: SlotName, type: PromptContentType = 'text') => {
    const oldAssetId = slot === 'question' ? questionUnassignedId : answerUnassignedId;
    const persistedSlot = getSlot(existing, slot);
    if (slot === 'question') {
      setQuestionMedia(null);
      setQuestionUnassignedId(null);
      setQuestionRemoval(persistedSlot);
      setValue('question_type', type, { shouldDirty: true, shouldValidate: true });
      setValue('question_media_asset_id', null, { shouldDirty: true, shouldValidate: true });
    } else {
      setAnswerMedia(null);
      setAnswerUnassignedId(null);
      setAnswerRemoval(persistedSlot);
      setValue('answer_type', type, { shouldDirty: true, shouldValidate: true });
      setValue('answer_media_asset_id', null, { shouldDirty: true, shouldValidate: true });
    }
    setLocalMediaChange(true);
    await cleanupAsset(oldAssetId);
  };

  const changeSlotType = (slot: SlotName, type: PromptContentType) => {
    const currentMedia = slot === 'question' ? questionMedia : answerMedia;
    if (currentMedia) {
      void removeSlot(slot);
      return;
    }
    setValue(slot === 'question' ? 'question_type' : 'answer_type', type, {
      shouldDirty: true,
      shouldValidate: true,
    });
  };

  const acceptUploadedAsset = (slot: SlotName, asset: MediaAsset) => {
    const previousId = slot === 'question' ? questionUnassignedId : answerUnassignedId;
    const reference = asReference(asset);
    if (slot === 'question') {
      setQuestionMedia(reference);
      setQuestionUnassignedId(asset.id);
      setValue('question_media_asset_id', asset.id, { shouldDirty: true, shouldValidate: true });
    } else {
      setAnswerMedia(reference);
      setAnswerUnassignedId(asset.id);
      setValue('answer_media_asset_id', asset.id, { shouldDirty: true, shouldValidate: true });
    }
    setLocalMediaChange(true);
    if (previousId !== null && previousId !== asset.id) void cleanupAsset(previousId);
  };

  const restorePersistedState = () => {
    if (!existing) return;
    const uploadedAssetIds = [questionUnassignedId, answerUnassignedId];
    syncFromPrompt(existing);
    for (const assetId of uploadedAssetIds) void cleanupAsset(assetId);
  };

  const deleteDetachedAssets = async (values: SlotValues) => {
    if (!existing) return;
    const detachedIds = [
      existing.question_media_asset_id !== values.question_media_asset_id
        ? existing.question_media_asset_id
        : null,
      existing.answer_media_asset_id !== values.answer_media_asset_id
        ? existing.answer_media_asset_id
        : null,
    ];
    for (const assetId of detachedIds) {
      if (assetId === null) continue;
      try {
        await deleteMedia(assetId);
      } catch {
        // Shared attachment cleanup can fail without invalidating saved prompt.
      }
    }
  };

  const onSubmit = handleSubmit(async (values) => {
    try {
      const saved = existing
        ? await update.mutateAsync({
            promptId: existing.id,
            payload: (() => {
              const { order: _order, ...payload } = values;
              return payload;
            })(),
          })
        : await create.mutateAsync(values);
      await deleteDetachedAssets(values);
      const category = await queryClient.fetchQuery({
        queryKey: queryKeys.categories.detail(categoryId),
        queryFn: () => getCategory(categoryId),
      });
      const savedPrompt = category.prompts.find((prompt) => prompt.id === saved.id);
      if (savedPrompt) syncFromPrompt(savedPrompt);
    } catch {
      restorePersistedState();
    }
  });

  const handleDelete = async () => {
    if (!existing) return;
    if (!window.confirm('Delete this prompt?')) return;
    await remove.mutateAsync(existing.id);
  };

  const busy =
    create.isPending ||
    update.isPending ||
    remove.isPending ||
    questionUploading ||
    answerUploading;
  const questionTypeRegistration = register('question_type');
  const answerTypeRegistration = register('answer_type');

  return (
    <form
      className="space-y-2 rounded-md border border-slate-800 bg-slate-900/50 p-3"
      onSubmit={onSubmit}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Prompt {order}</h3>
        <span className="text-xs text-slate-400">Score: {order * 100}</span>
      </div>
      <Field
        label="Question instruction / caption"
        htmlFor={`q-${order}`}
        error={errors.question?.message}
        help="Required. Images need an instruction. For audio/video, keep the clue short and don't reveal the answer."
      >
        <Input id={`q-${order}`} invalid={!!errors.question} {...register('question')} />
      </Field>
      <Field label="Question type" htmlFor={`question-type-${order}`}>
        <select
          id={`question-type-${order}`}
          className="h-11 w-full rounded-md border border-slate-700 bg-slate-950 px-3 text-slate-100"
          {...questionTypeRegistration}
          disabled={busy}
          onChange={(event) => {
            questionTypeRegistration.onChange(event);
            changeSlotType('question', event.target.value as PromptContentType);
          }}
        >
          {contentTypeOptions.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </Field>
      <MediaControl
        slot="question"
        contentType={questionType}
        media={questionMedia}
        unassignedAssetId={questionUnassignedId}
        disabled={busy}
        onUploaded={(asset) => acceptUploadedAsset('question', asset)}
        onRemove={() => removeSlot('question')}
        onUploadStateChange={setQuestionUploading}
      />
      {errors.question_media_asset_id ? (
        <p className="text-sm text-rose-300">{errors.question_media_asset_id.message}</p>
      ) : null}
      <Field
        label="Canonical expected answer"
        htmlFor={`a-${order}`}
        error={errors.answer?.message}
        help="Required for every reveal type. The host judges answers against this text."
      >
        <Input id={`a-${order}`} invalid={!!errors.answer} {...register('answer')} />
      </Field>
      <Field label="Answer reveal type" htmlFor={`answer-type-${order}`}>
        <select
          id={`answer-type-${order}`}
          className="h-11 w-full rounded-md border border-slate-700 bg-slate-950 px-3 text-slate-100"
          {...answerTypeRegistration}
          disabled={busy}
          onChange={(event) => {
            answerTypeRegistration.onChange(event);
            changeSlotType('answer', event.target.value as PromptContentType);
          }}
        >
          {contentTypeOptions.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </Field>
      <MediaControl
        slot="answer"
        contentType={answerType}
        media={answerMedia}
        unassignedAssetId={answerUnassignedId}
        disabled={busy}
        onUploaded={(asset) => acceptUploadedAsset('answer', asset)}
        onRemove={() => removeSlot('answer')}
        onUploadStateChange={setAnswerUploading}
      />
      {errors.answer_media_asset_id ? (
        <p className="text-sm text-rose-300">{errors.answer_media_asset_id.message}</p>
      ) : null}
      <div className="flex justify-between gap-2">
        {existing ? (
          <Button type="button" variant="danger" size="sm" disabled={busy} onClick={handleDelete}>
            Delete
          </Button>
        ) : (
          <span />
        )}
        <Button type="submit" size="sm" disabled={!isDirty || busy}>
          {existing ? 'Save' : 'Add'}
        </Button>
      </div>
    </form>
  );
};

export default PromptEditor;
