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
  const audio = useContext(GameAudioContext);
  const { beginPromptMediaPlayback, enabled, endPromptMediaPlayback } = audio ?? {
    beginPromptMediaPlayback: undefined,
    enabled: false,
    endPromptMediaPlayback: undefined,
  };
  const volume = audio?.volume;
  const mediaElementRef = useRef<HTMLMediaElement | null>(null);
  const mediaSrc = src ?? media?.url;
  const isPlayableMedia = contentType === 'audio' || contentType === 'video';
  const mediaIdentity = `${playbackId ?? 'preview'}:${mediaSrc ?? ''}`;
  const setMediaElement = useCallback((element: HTMLMediaElement | null) => {
    mediaElementRef.current = element;
  }, []);

  // The navbar sound controls are global: mirror them onto the element. iOS Safari ignores
  // `volume` (always 1) but honors `muted`, so sound off and volume 0 still silence it there.
  useEffect(() => {
    const mediaElement = mediaElementRef.current;
    if (!mediaElement || volume === undefined) return;
    mediaElement.volume = volume;
    mediaElement.muted = !enabled || volume === 0;
  }, [enabled, mediaIdentity, volume]);

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
        decoding="async"
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
