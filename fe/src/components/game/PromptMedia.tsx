import { useCallback, useContext, useEffect, useRef, useState } from 'react';

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
  const autoplay = playbackId !== undefined && enabled;
  // Mobile browsers reject play() without a user gesture; remember which clue was blocked.
  const [blockedIdentity, setBlockedIdentity] = useState<string | null>(null);
  const blocked = blockedIdentity === mediaIdentity;
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
    const mediaElement = mediaElementRef.current;
    if (!isPlayableMedia || !autoplay || !mediaElement) return;
    mediaElement.play().catch((error: unknown) => {
      if (error instanceof DOMException && error.name === 'NotAllowedError') {
        setBlockedIdentity(mediaIdentity);
      } else if (!(error instanceof DOMException && error.name === 'AbortError')) {
        console.error('Prompt media failed to play', error);
      }
    });
  }, [autoplay, isPlayableMedia, mediaIdentity]);

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
  const tapToPlay = blocked ? (
    <button
      type="button"
      onClick={() => {
        setBlockedIdentity(null);
        void mediaElementRef.current?.play();
      }}
      className="rounded-md bg-amber-400 px-4 py-2 text-sm font-bold text-slate-950 hover:bg-amber-300"
    >
      Tap to play
    </button>
  ) : null;
  if (contentType === 'audio') {
    return (
      <>
        <audio
          key={mediaIdentity}
          ref={setMediaElement}
          controls
          autoPlay={autoplay}
          preload="metadata"
          className={`w-full max-w-xl ${className}`}
          src={mediaSrc}
          onPlay={() => playbackId && beginPromptMediaPlayback?.(playbackId)}
          onPause={() => playbackId && endPromptMediaPlayback?.(playbackId)}
          onEnded={() => playbackId && endPromptMediaPlayback?.(playbackId)}
          onError={() => playbackId && endPromptMediaPlayback?.(playbackId)}
        />
        {tapToPlay}
      </>
    );
  }
  return (
    <>
      <video
        key={mediaIdentity}
        ref={setMediaElement}
        controls
        playsInline
        autoPlay={autoplay}
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
      {tapToPlay}
    </>
  );
};

export default PromptMedia;
