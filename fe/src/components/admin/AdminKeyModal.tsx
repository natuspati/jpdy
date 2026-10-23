import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';

import { claimAdminKey } from '@/api/auth';
import { queryKeys } from '@/api/queryKeys';
import Button from '@/components/ui/Button';
import Field from '@/components/ui/Field';
import Input from '@/components/ui/Input';
import Modal from '@/components/ui/Modal';
import { AdminKeyForm } from '@/schemas';

/**
 * One guess per account. Every failure (wrong key, spent attempt, feature off) is a silent
 * redirect home, so nothing here may toast or explain.
 */
const AdminKeyModal = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AdminKeyForm>({
    resolver: zodResolver(AdminKeyForm),
    defaultValues: { key: '' },
  });

  const mutation = useMutation({
    mutationFn: (values: AdminKeyForm) => claimAdminKey(values.key),
    onError: () => navigate('/', { replace: true }),
    // The attempt is spent either way; refresh the cached user (role / attempted) before moving on.
    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.me() }),
  });

  // Closing without submitting keeps the attempt.
  const leave = () => {
    if (!mutation.isPending) navigate('/', { replace: true });
  };

  return (
    <Modal open onClose={leave} title="Admin access">
      <form className="space-y-3" onSubmit={handleSubmit((values) => mutation.mutate(values))}>
        <Field label="Admin key" htmlFor="admin-key" error={errors.key?.message}>
          <Input
            id="admin-key"
            type="password"
            autoComplete="off"
            autoFocus
            invalid={!!errors.key}
            {...register('key')}
          />
        </Field>
        <Button type="submit" fullWidth disabled={mutation.isPending}>
          {mutation.isPending ? 'Checking…' : 'Continue'}
        </Button>
      </form>
    </Modal>
  );
};

export default AdminKeyModal;
