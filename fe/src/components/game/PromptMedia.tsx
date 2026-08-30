import { useCallback, useContext, useEffect, useRef } from 'react';

import { GameAudioContext } from '@/audio/gameAudioContext';
import type { MediaReference, PromptContentType } from '@/schemas';

interface Props {
  contentType: PromptContentType;
  media: MediaReference | null | undefined;
  alt: string;
  src?: string | null;
  playbackId?: string;
  className?: string;
}

const PromptMedia = ({
  contentType,
  media,
  alt,
  src = null,
  playbackId,
  className = '',
}: Props) => {
  const { beginPromptMediaPlayback, enabled, endPromptMediaPlayback } = useContext(
    GameAudioContext,
  ) ?? {
    beginPromptMediaPlayback: undefined,
    enabled: false,
    endPromptMediaPlayback: undefined,
  };
  const mediaElementRef = useRef<HTMLMediaElement | null>(null);
  const mediaSrc = src ?? media?.url;
  const isPlayableMedia = contentType === 'audio' || contentType === 'video';
  const mediaIdentity = `${playbackId ?? 'preview'}:${mediaSrc ?? ''}`;
  const setMediaElement = useCallback((element: HTMLMediaElement | null) => {
    mediaElementRef.current = element;
  }, []);

  useEffect(() => {
    if (!isPlayableMedia) return;
    const mediaElement = mediaElementRef.current;
    return () => {
      mediaElement?.pause();
      if (playbackId) endPromptMediaPlayback?.(playbackId);
    };
  }, [endPromptMediaPlayback, isPlayableMedia, mediaSrc, playbackId]);

  if (contentType === 'text' || !mediaSrc) return null;

  if (contentType === 'image') {
    return (
      <img
        src={mediaSrc}
        alt={alt}
        className={`max-h-full max-w-full rounded-lg object-contain ${className}`}
      />
    );
  }
  if (contentType === 'audio') {
    return (
      <audio
        key={mediaIdentity}
        ref={setMediaElement}
        controls
        autoPlay={playbackId !== undefined && enabled}
        preload="metadata"
        className={`w-full max-w-xl ${className}`}
        src={mediaSrc}
        onPlay={() => playbackId && beginPromptMediaPlayback?.(playbackId)}
        onPause={() => playbackId && endPromptMediaPlayback?.(playbackId)}
        onEnded={() => playbackId && endPromptMediaPlayback?.(playbackId)}
        onError={() => playbackId && endPromptMediaPlayback?.(playbackId)}
      />
    );
  }
  return (
    <video
      key={mediaIdentity}
      ref={setMediaElement}
      controls
      autoPlay={playbackId !== undefined && enabled}
      preload="metadata"
      className={`max-h-full max-w-full rounded-lg object-contain ${className}`}
      src={mediaSrc}
      onPlay={() => playbackId && beginPromptMediaPlayback?.(playbackId)}
      onPause={() => playbackId && endPromptMediaPlayback?.(playbackId)}
      onEnded={() => playbackId && endPromptMediaPlayback?.(playbackId)}
      onError={() => playbackId && endPromptMediaPlayback?.(playbackId)}
    >
      <track kind="captions" />
    </video>
  );
};

export default PromptMedia;
