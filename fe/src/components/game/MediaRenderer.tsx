import { assetUrl } from '@/services/media/assetUrl';
import type { AnswerTypeEnum, QuestionTypeEnum } from '@/schemas';

interface Props {
  type: QuestionTypeEnum | AnswerTypeEnum;
  value: string;
  className?: string;
}

const MediaRenderer = ({ type, value, className = '' }: Props) => {
  if (type === 'text') {
    return (
      <p className={`text-balance text-center text-[clamp(1.25rem,4vw,2.5rem)] ${className}`}>
        {value}
      </p>
    );
  }
  if (type === 'image') {
    return (
      <img
        src={assetUrl(value)}
        alt=""
        className={`mx-auto max-h-[60vh] max-w-full rounded-md object-contain ${className}`}
      />
    );
  }
  if (type === 'audio') {
    return <audio controls src={assetUrl(value)} className={`mx-auto w-full ${className}`} />;
  }
  return (
    <video
      controls
      src={assetUrl(value)}
      className={`mx-auto max-h-[60vh] max-w-full rounded-md ${className}`}
    />
  );
};

export default MediaRenderer;
