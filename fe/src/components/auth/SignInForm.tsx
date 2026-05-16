import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { signIn } from '@/api/auth';
import { ApiError } from '@/api/errors';
import Button from '@/components/ui/Button';
import Field from '@/components/ui/Field';
import Input from '@/components/ui/Input';
import { useAuth } from '@/hooks/useAuth';
import { SignInForm as SignInFormSchema } from '@/schemas';
import { toastError } from '@/store/toastStore';

const SignInForm = () => {
  const { setToken } = useAuth();
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignInFormSchema>({
    resolver: zodResolver(SignInFormSchema),
    defaultValues: { username: '', password: '' },
  });

  const mutation = useMutation({
    mutationFn: (values: SignInFormSchema) => signIn(values.username, values.password),
    onSuccess: (data) => {
      setToken(data.access_token);
      queryClient.invalidateQueries();
    },
    onError: (e) => {
      toastError(e instanceof ApiError ? e.detail : 'Sign-in failed');
    },
  });

  return (
    <form className="space-y-3" onSubmit={handleSubmit((values) => mutation.mutate(values))}>
      <Field label="Username" htmlFor="username" error={errors.username?.message}>
        <Input
          id="username"
          autoComplete="username"
          autoFocus
          invalid={!!errors.username}
          {...register('username')}
        />
      </Field>
      <Field label="Password" htmlFor="password" error={errors.password?.message}>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          invalid={!!errors.password}
          {...register('password')}
        />
      </Field>
      <Button type="submit" fullWidth disabled={isSubmitting || mutation.isPending}>
        {isSubmitting || mutation.isPending ? 'Signing in…' : 'Sign in'}
      </Button>
    </form>
  );
};

export default SignInForm;
