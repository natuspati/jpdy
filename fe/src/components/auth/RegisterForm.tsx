import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import { register as registerApi, signIn } from '@/api/auth';
import { ApiError } from '@/api/errors';
import Button from '@/components/ui/Button';
import Field from '@/components/ui/Field';
import Input from '@/components/ui/Input';
import { useAuth } from '@/hooks/useAuth';
import { RegisterForm as RegisterFormSchema } from '@/schemas';
import { toastError, toastSuccess } from '@/store/toastStore';

const RegisterForm = () => {
  const navigate = useNavigate();
  const { setToken } = useAuth();
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormSchema>({
    resolver: zodResolver(RegisterFormSchema),
    defaultValues: { username: '', password: '', passwordConfirm: '', inviteCode: '' },
  });

  const mutation = useMutation({
    mutationFn: async (values: RegisterFormSchema) => {
      await registerApi(values.username, values.password, values.inviteCode);
      return signIn(values.username, values.password);
    },
    onSuccess: (data) => {
      setToken(data.access_token);
      queryClient.invalidateQueries();
      toastSuccess('Welcome!');
      navigate('/');
    },
    onError: (e) => {
      toastError(e instanceof ApiError ? e.detail : 'Registration failed');
    },
  });

  return (
    <form className="space-y-3" onSubmit={handleSubmit((values) => mutation.mutate(values))}>
      <Field label="Username" htmlFor="username" error={errors.username?.message}>
        <Input
          id="username"
          autoComplete="username"
          invalid={!!errors.username}
          {...register('username')}
        />
      </Field>
      <Field label="Password" htmlFor="password" error={errors.password?.message}>
        <Input
          id="password"
          type="password"
          autoComplete="new-password"
          invalid={!!errors.password}
          {...register('password')}
        />
      </Field>
      <Field
        label="Confirm password"
        htmlFor="passwordConfirm"
        error={errors.passwordConfirm?.message}
      >
        <Input
          id="passwordConfirm"
          type="password"
          autoComplete="new-password"
          invalid={!!errors.passwordConfirm}
          {...register('passwordConfirm')}
        />
      </Field>
      <Field label="Invite code" htmlFor="inviteCode" error={errors.inviteCode?.message}>
        <Input
          id="inviteCode"
          autoComplete="off"
          invalid={!!errors.inviteCode}
          {...register('inviteCode')}
        />
      </Field>
      <Button type="submit" fullWidth disabled={isSubmitting || mutation.isPending}>
        {isSubmitting || mutation.isPending ? 'Creating account…' : 'Create account'}
      </Button>
    </form>
  );
};

export default RegisterForm;
