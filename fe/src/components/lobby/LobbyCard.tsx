import { useNavigate } from 'react-router-dom';

import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import type { LobbyWithCategories } from '@/schemas';

interface Props {
  lobby: LobbyWithCategories;
}

const LobbyCard = ({ lobby }: Props) => {
  const navigate = useNavigate();
  const ownerName = lobby.owner?.username ?? '(deleted user)';
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-100">Lobby #{lobby.id}</h3>
          <p className="text-sm text-slate-400">Host: {ownerName}</p>
          <p className="text-xs text-slate-500">Categories: {lobby.prompt_categories.length}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge tone="info">{lobby.state}</Badge>
          <Button size="sm" onClick={() => navigate(`/lobby/${lobby.id}`)}>
            Join
          </Button>
        </div>
      </div>
    </Card>
  );
};

export default LobbyCard;
