import { type InputHTMLAttributes, forwardRef } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ invalid, className = '', ...rest }, ref) => {
    const cls = [
      'block w-full rounded-md bg-slate-900 px-3 py-2 text-slate-100',
      'border focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-950',
      invalid
        ? 'border-rose-500 focus:ring-rose-500'
        : 'border-slate-700 focus:border-amber-400 focus:ring-amber-400',
      'placeholder:text-slate-500',
      className,
    ].join(' ');
    return <input ref={ref} className={cls} {...rest} />;
  },
);
Input.displayName = 'Input';

export default Input;
