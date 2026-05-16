import { Link } from 'react-router-dom';

import RegisterForm from '@/components/auth/RegisterForm';
import Card from '@/components/ui/Card';

const RegisterPage = () => (
  <div className="mx-auto max-w-sm space-y-4">
    <Card>
      <h1 className="mb-3 text-xl font-bold">Create account</h1>
      <RegisterForm />
    </Card>
    <p className="text-center text-sm text-slate-400">
      Already have an account?{' '}
      <Link to="/" className="font-medium text-amber-300 hover:underline">
        Sign in
      </Link>
    </p>
  </div>
);

export default RegisterPage;
