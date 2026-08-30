import Button from '@/components/ui/Button';
import Modal from '@/components/ui/Modal';
import type { MyLobby } from '@/schemas';

interface Props {
  lobby: MyLobby | null;
  pending: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

const DeleteLobbyModal = ({ lobby, pending, onClose, onConfirm }: Props) => (
  <Modal open={lobby !== null} onClose={pending ? () => undefined : onClose} title="Delete lobby">
    {lobby ? (
      <div className="space-y-4">
        <p className="text-slate-200">
          Delete lobby <strong>#{lobby.id}</strong> in <strong>{lobby.state}</strong> state?
        </p>
        <p className="text-sm text-slate-400">
          This cannot be undone. Connected players will be told the host deleted the lobby, then
          disconnected.
        </p>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" disabled={pending} onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" variant="danger" disabled={pending} onClick={onConfirm}>
            {pending ? 'Deleting…' : 'Delete lobby'}
          </Button>
        </div>
      </div>
    ) : null}
  </Modal>
);

export default DeleteLobbyModal;
