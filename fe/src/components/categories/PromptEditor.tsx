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
import { PromptCreate, type PromptInDB } from '@/schemas';

type SlotValues = {
  question: string;
  answer: string;
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
    resolver: zodResolver(PromptCreate.pick({ question: true, answer: true })),
    defaultValues: {
      question: existing?.question ?? '',
      answer: existing?.answer ?? '',
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    if (existing) {
      await update.mutateAsync({ promptId: existing.id, payload: values });
    } else {
      await create.mutateAsync({
        ...values,
        question_type: 'text',
        answer_type: 'text',
        order,
      });
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
