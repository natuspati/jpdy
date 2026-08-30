import { useRef, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import PromptMedia from '@/components/game/PromptMedia';
import Button from '@/components/ui/Button';
import Field from '@/components/ui/Field';
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
  label: string;
  contentType: PromptContentType;
  media: MediaReference | null;
  disabled: boolean;
  onUploaded: (asset: MediaAsset) => void;
  onRemove: () => void;
}

const fileRules: Record<MediaKind, { accept: string; maxBytes: number; guidance: string }> = {
  image: {
    accept: 'image/jpeg,image/png,image/webp',
    maxBytes: 10 * 1024 * 1024,
    guidance: 'JPEG, PNG, or WebP. Max 10 MB.',
  },
  audio: {
    accept: 'audio/mpeg,audio/mp4,audio/aac,audio/ogg,.mp3,.m4a,.aac,.ogg',
    maxBytes: 20 * 1024 * 1024,
    guidance: 'MP3, M4A/AAC, or Ogg. Max 20 MB.',
  },
  video: {
    accept: 'video/mp4,.mp4',
    maxBytes: 100 * 1024 * 1024,
    guidance: 'MP4 (H.264/AAC). Max 100 MB.',
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

const MediaControl = ({
  label,
  contentType,
  media,
  disabled,
  onUploaded,
  onRemove,
}: MediaControlProps) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const upload = useUploadMedia();
  const mediaKind = mediaKindFor(contentType);

  if (!mediaKind) return null;

  const rules = fileRules[mediaKind];
  const uploadSelected = async () => {
    if (!selectedFile) {
      toastError(`Choose ${label.toLowerCase()} media first`);
      return;
    }
    if (selectedFile.size > rules.maxBytes) {
      toastError(`${label} file exceeds ${rules.maxBytes / (1024 * 1024)} MB limit`);
      return;
    }
    const asset = await upload.mutateAsync({ file: selectedFile, kind: mediaKind });
    onUploaded(asset);
    setSelectedFile(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div className="space-y-2 rounded border border-slate-700 bg-slate-950/30 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-slate-200">{label} media</p>
        {media ? (
          <Button type="button" size="sm" variant="ghost" disabled={disabled} onClick={onRemove}>
            Remove
          </Button>
        ) : null}
      </div>
      {media ? (
        <PromptMedia contentType={contentType} media={media} alt={`${label} media preview`} />
      ) : (
        <p className="text-sm text-slate-400">No uploaded {mediaKind} selected.</p>
      )}
      <p className="text-xs text-slate-400">{rules.guidance}</p>
      <input
        ref={inputRef}
        type="file"
        accept={rules.accept}
        disabled={disabled || upload.isPending}
        onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
      />
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={disabled || !selectedFile || upload.isPending}
          onClick={uploadSelected}
        >
          {upload.isPending ? 'Uploading…' : media ? 'Replace upload' : 'Upload media'}
        </Button>
        {selectedFile ? <span className="text-xs text-slate-400">{selectedFile.name}</span> : null}
      </div>
    </div>
  );
};

const PromptEditor = ({ categoryId, order, existing }: Props) => {
  const create = useCreatePrompt(categoryId);
  const update = useUpdatePrompt(categoryId);
  const remove = useDeletePrompt(categoryId);
  const [questionMedia, setQuestionMedia] = useState<MediaReference | null>(
    existing?.question_content.media ?? null,
  );
  const [answerMedia, setAnswerMedia] = useState<MediaReference | null>(
    existing?.answer_content.media ?? null,
  );
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

  const onSubmit = handleSubmit(async (values) => {
    if (existing) {
      const { order: _order, ...payload } = values;
      await update.mutateAsync({ promptId: existing.id, payload });
    } else {
      await create.mutateAsync(values);
    }
    reset(values);
  });

  const handleDelete = async () => {
    if (!existing) return;
    if (!window.confirm('Delete this prompt?')) return;
    await remove.mutateAsync(existing.id);
  };

  const busy = create.isPending || update.isPending || remove.isPending;

  return (
    <form
      className="space-y-3 rounded-md border border-slate-800 bg-slate-900/50 p-3"
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
      >
        <Input id={`q-${order}`} invalid={!!errors.question} {...register('question')} />
      </Field>
      <p className="text-xs text-slate-400">
        Images need an instruction. Audio/video should use concise clues without answer-revealing
        transcripts.
      </p>
      <Field label="Question type" htmlFor={`question-type-${order}`}>
        <select
          id={`question-type-${order}`}
          className="h-11 w-full rounded-md border border-slate-700 bg-slate-950 px-3 text-slate-100"
          {...register('question_type', {
            onChange: (event) => {
              if (event.target.value === 'text') {
                setQuestionMedia(null);
                setValue('question_media_asset_id', null, { shouldDirty: true });
              }
            },
          })}
        >
          {contentTypeOptions.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </Field>
      <MediaControl
        label="Question"
        contentType={questionType}
        media={questionMedia}
        disabled={busy}
        onUploaded={(asset) => {
          setQuestionMedia(asReference(asset));
          setValue('question_media_asset_id', asset.id, {
            shouldDirty: true,
            shouldValidate: true,
          });
        }}
        onRemove={() => {
          setQuestionMedia(null);
          setValue('question_media_asset_id', null, { shouldDirty: true, shouldValidate: true });
        }}
      />
      {errors.question_media_asset_id ? (
        <p className="text-sm text-rose-300">{errors.question_media_asset_id.message}</p>
      ) : null}
      <Field
        label="Canonical expected answer"
        htmlFor={`a-${order}`}
        error={errors.answer?.message}
      >
        <Input id={`a-${order}`} invalid={!!errors.answer} {...register('answer')} />
      </Field>
      <p className="text-xs text-slate-400">
        Required for every reveal type. Host judgment and answer matching always use this text.
      </p>
      <Field label="Answer reveal type" htmlFor={`answer-type-${order}`}>
        <select
          id={`answer-type-${order}`}
          className="h-11 w-full rounded-md border border-slate-700 bg-slate-950 px-3 text-slate-100"
          {...register('answer_type', {
            onChange: (event) => {
              if (event.target.value === 'text') {
                setAnswerMedia(null);
                setValue('answer_media_asset_id', null, { shouldDirty: true });
              }
            },
          })}
        >
          {contentTypeOptions.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </Field>
      <MediaControl
        label="Answer reveal"
        contentType={answerType}
        media={answerMedia}
        disabled={busy}
        onUploaded={(asset) => {
          setAnswerMedia(asReference(asset));
          setValue('answer_media_asset_id', asset.id, { shouldDirty: true, shouldValidate: true });
        }}
        onRemove={() => {
          setAnswerMedia(null);
          setValue('answer_media_asset_id', null, { shouldDirty: true, shouldValidate: true });
        }}
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
