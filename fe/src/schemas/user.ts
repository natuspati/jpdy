import { z } from 'zod';

// Mirrors UserPublicSchema
export const UserPublic = z.object({
  id: z.number().int(),
  username: z.string(),
});
export type UserPublic = z.infer<typeof UserPublic>;

// Form-side: register
export const RegisterForm = z
  .object({
    username: z.string().min(3, 'At least 3 characters').max(20, 'At most 20 characters'),
    password: z.string().min(6, 'At least 6 characters').max(20, 'At most 20 characters'),
    passwordConfirm: z.string(),
  })
  .refine((data) => data.password === data.passwordConfirm, {
    message: 'Passwords do not match',
    path: ['passwordConfirm'],
  });
export type RegisterForm = z.infer<typeof RegisterForm>;

// Mirrors UserCreateSchema (sent to BE — note: BE computes hashed_password server-side from `password`)
export const UserCreate = z.object({
  username: z.string().min(3).max(20),
  password: z.string().min(6).max(20),
});
export type UserCreate = z.infer<typeof UserCreate>;

// Form-side: sign-in
export const SignInForm = z.object({
  username: z.string().min(1, 'Required'),
  password: z.string().min(1, 'Required'),
});
export type SignInForm = z.infer<typeof SignInForm>;

// TokenSchema
export const TokenResponse = z.object({
  access_token: z.string(),
  token_type: z.string(),
});
export type TokenResponse = z.infer<typeof TokenResponse>;
