import type { MediaReference, PromptContentType } from '@/schemas';

interface Props {
  contentType: PromptContentType;
  media: MediaReference | null | undefined;
  alt: string;
  src?: string | null;
}

const PromptMedia = ({ contentType, media, alt, src = null }: Props) => {
  const mediaSrc = src ?? media?.url;
  if (contentType === 'text' || !mediaSrc) return null;

  if (contentType === 'image') {
    return (
      <img
        src={mediaSrc}
        alt={alt}
        className="max-h-[28rem] w-auto max-w-full rounded-lg object-contain"
      />
    );
  }
  if (contentType === 'audio') {
    return <audio controls preload="metadata" className="w-full max-w-xl" src={mediaSrc} />;
  }
  return (
    <video
      controls
      preload="metadata"
      className="max-h-[28rem] w-full max-w-3xl rounded-lg"
      src={mediaSrc}
    >
      <track kind="captions" />
    </video>
  );
};

export default PromptMedia;
