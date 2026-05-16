import { useState } from 'react';

import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { SubmitAnswerPayload } from '@/schemas';

interface Props {
  onSubmit: (text: string) => boolean | void;
  disabled?: boolean;
}

const AnswerInput = ({ onSubmit, disabled }: Props) => {
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = SubmitAnswerPayload.safeParse({ text });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? 'Invalid answer');
      return;
    }
    setError(null);
    onSubmit(parsed.data.text);
    setText('');
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="sticky bottom-0 left-0 right-0 z-10 -mx-4 border-t border-slate-800 bg-slate-950/95 p-3 sm:static sm:m-0 sm:rounded-md sm:border sm:bg-slate-900/70"
    >
      <div className="flex gap-2">
        <Input
          autoFocus
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type your answer…"
          disabled={disabled}
          invalid={!!error}
          maxLength={500}
        />
        <Button type="submit" disabled={disabled || text.length === 0}>
          Send
        </Button>
      </div>
      {error ? <p className="mt-1 text-xs text-rose-400">{error}</p> : null}
    </form>
  );
};

export default AnswerInput;
