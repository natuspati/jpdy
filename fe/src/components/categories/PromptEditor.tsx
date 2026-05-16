import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import Button from '@/components/ui/Button';
import Field from '@/components/ui/Field';
import Input from '@/components/ui/Input';
import {
  useCreatePrompt,
  useDeletePrompt,
  useUpdatePrompt,
} from '@/hooks/usePromptCategories';
import {
  AnswerTypeEnum,
  PromptCreate,
  PromptUpdate,
  QuestionTypeEnum,
  type PromptInDB,
} from '@/schemas';

type SlotValues = {
  question: string;
  question_type: 'text' | 'image' | 'audio' | 'video';
  answer: string;
  answer_type: 'text' | 'image' | 'audio' | 'video';
};

interface Props {
  categoryId: number;
  order: number;
  existing: PromptInDB | undefined;
}

const PromptEditor = ({ categoryId, order, existing }: Props) => {
  const create = useCreatePrompt(categoryId);
  const update = useUpdatePrompt(categoryId);
  const remove = useDeletePrompt(categoryId);

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
    reset,
  } = useForm<SlotValues>({
    resolver: zodResolver(
      existing
        ? PromptUpdate.transform((d) => d as SlotValues)
        : PromptCreate.omit({ order: true }).transform((d) => d as SlotValues),
    ),
    defaultValues: {
      question: existing?.question ?? '',
      question_type: existing?.question_type ?? 'text',
      answer: existing?.answer ?? '',
      answer_type: existing?.answer_type ?? 'text',
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    if (existing) {
      await update.mutateAsync({ promptId: existing.id, payload: values });
    } else {
      await create.mutateAsync({ ...values, order });
    }
    reset(values);
  });

  const handleDelete = async () => {
    if (!existing) return;
    if (!window.confirm('Delete this prompt?')) return;
    await remove.mutateAsync(existing.id);
  };

  return (
    <form
      className="space-y-2 rounded-md border border-slate-800 bg-slate-900/50 p-3"
      onSubmit={onSubmit}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Prompt {order}</h3>
        <span className="text-xs text-slate-400">Score: {order * 100}</span>
      </div>
      <Field label="Question" htmlFor={`q-${order}`} error={errors.question?.message}>
        <Input id={`q-${order}`} invalid={!!errors.question} {...register('question')} />
      </Field>
      <div className="grid grid-cols-2 gap-2">
        <Field
          label="Q type"
          htmlFor={`qt-${order}`}
          error={errors.question_type?.message}
        >
          <select
            id={`qt-${order}`}
            className="h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-2 text-slate-100"
            {...register('question_type')}
          >
            {QuestionTypeEnum.options.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label="A type"
          htmlFor={`at-${order}`}
          error={errors.answer_type?.message}
        >
          <select
            id={`at-${order}`}
            className="h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-2 text-slate-100"
            {...register('answer_type')}
          >
            {AnswerTypeEnum.options.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <Field label="Answer" htmlFor={`a-${order}`} error={errors.answer?.message}>
        <Input id={`a-${order}`} invalid={!!errors.answer} {...register('answer')} />
      </Field>
      <div className="flex justify-between gap-2">
        {existing ? (
          <Button type="button" variant="danger" size="sm" onClick={handleDelete}>
            Delete
          </Button>
        ) : (
          <span />
        )}
        <Button
          type="submit"
          size="sm"
          disabled={!isDirty || create.isPending || update.isPending}
        >
          {existing ? 'Save' : 'Add'}
        </Button>
      </div>
    </form>
  );
};

export default PromptEditor;
