import type { MediaReference, PromptContentType } from '@/schemas';

interface Props {
  contentType: PromptContentType;
  media: MediaReference | null | undefined;
  alt: string;
}

const PromptMedia = ({ contentType, media, alt }: Props) => {
  if (contentType === 'text' || !media) return null;

  if (contentType === 'image') {
    return (
      <img
        src={media.url}
        alt={alt}
        className="max-h-[28rem] w-auto max-w-full rounded-lg object-contain"
      />
    );
  }
  if (contentType === 'audio') {
    return <audio controls preload="metadata" className="w-full max-w-xl" src={media.url} />;
  }
  return (
    <video
      controls
      preload="metadata"
      className="max-h-[28rem] w-full max-w-3xl rounded-lg"
      src={media.url}
    >
      <track kind="captions" />
    </video>
  );
};

export default PromptMedia;
