import { type HTMLAttributes } from 'react';

const Card = ({ className = '', ...rest }: HTMLAttributes<HTMLDivElement>) => {
  const cls = ['rounded-lg border border-slate-800 bg-slate-900/60 p-4 shadow-lg', className].join(
    ' ',
  );
  return <div className={cls} {...rest} />;
};

export default Card;
