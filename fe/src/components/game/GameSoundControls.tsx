import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import { useGameAudio } from '@/audio/useGameAudio';

const GameSoundControls = () => {
  const { enabled, volume, blockedMessage, enableSound, toggleMuted, setVolume } = useGameAudio();

  return (
    <Card className="space-y-3">
      {!enabled ? (
        <Button fullWidth variant="secondary" onClick={() => void enableSound()}>
          Enable sound
        </Button>
      ) : (
        <>
          <Button fullWidth variant="secondary" onClick={toggleMuted}>
            Mute sound
          </Button>
          <label className="block space-y-1 text-sm text-slate-200">
            <span>Game volume: {Math.round(volume * 100)}%</span>
            <input
              className="w-full accent-amber-400"
              type="range"
              min="0"
              max="100"
              value={Math.round(volume * 100)}
              onChange={(event) => setVolume(Number(event.target.value) / 100)}
            />
          </label>
        </>
      )}
      {blockedMessage ? <p className="text-sm text-rose-300">{blockedMessage}</p> : null}
    </Card>
  );
};

export default GameSoundControls;
