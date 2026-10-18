import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';

import Button from '@/components/ui/Button';
import Field from '@/components/ui/Field';
import Input from '@/components/ui/Input';
import Modal from '@/components/ui/Modal';
import { useCreateCategory } from '@/hooks/usePromptCategories';
import { PromptCategoryCreate } from '@/schemas';

interface Props {
  open: boolean;
  onClose: () => void;
}

const CreateCategoryModal = ({ open, onClose }: Props) => {
  const navigate = useNavigate();
  const create = useCreateCategory();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PromptCategoryCreate>({
    resolver: zodResolver(PromptCategoryCreate),
    defaultValues: { name: '', kind: 'standard' },
  });

  const onSubmit = handleSubmit(async (values) => {
    const result = await create.mutateAsync(values);
    reset();
    onClose();
    navigate(`/categories/${result.id}`);
  });

  return (
    <Modal open={open} onClose={onClose} title="New category">
      <form className="space-y-3" onSubmit={onSubmit}>
        <Field label="Name" htmlFor="name" error={errors.name?.message}>
          <Input id="name" autoFocus invalid={!!errors.name} {...register('name')} />
        </Field>
        <Field
          label="Category kind"
          htmlFor="category-kind"
          hint="Kind cannot be changed after creation."
          error={errors.kind?.message}
        >
          <select
            id="category-kind"
            className="h-11 w-full rounded-md border border-slate-700 bg-slate-950 px-3 text-slate-100"
            {...register('kind')}
          >
            <option value="standard">Standard — five prompts</option>
            <option value="final">Final — one prompt, no fixed score</option>
          </select>
        </Field>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? 'Creating…' : 'Create'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default CreateCategoryModal;
