import { type ButtonHTMLAttributes, forwardRef } from 'react';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';
type Size = 'icon' | 'compact' | 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  fullWidth?: boolean;
}

const variantClasses: Record<Variant, string> = {
  primary: 'bg-amber-400 text-slate-900 hover:bg-amber-300 disabled:bg-amber-400/40',
  secondary: 'bg-slate-700 text-slate-50 hover:bg-slate-600 disabled:bg-slate-700/40',
  danger: 'bg-rose-600 text-white hover:bg-rose-500 disabled:bg-rose-600/40',
  ghost: 'bg-transparent text-slate-200 hover:bg-slate-800 disabled:text-slate-500',
};

const sizeClasses: Record<Size, string> = {
  icon: 'h-7 w-7 p-0 text-sm',
  compact: 'h-7 px-3 text-sm',
  sm: 'h-9 px-3 text-sm',
  md: 'h-11 px-4 text-base',
  lg: 'h-14 px-6 text-lg',
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', fullWidth, className = '', ...rest }, ref) => {
    const cls = [
      'inline-flex items-center justify-center rounded-md font-semibold transition-colors',
      'focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 focus:ring-offset-slate-950',
      'disabled:cursor-not-allowed',
      variantClasses[variant],
      sizeClasses[size],
      fullWidth ? 'w-full' : '',
      className,
    ]
      .filter(Boolean)
      .join(' ');
    return <button ref={ref} className={cls} {...rest} />;
  },
);
Button.displayName = 'Button';

export default Button;
