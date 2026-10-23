import Button from './Button';
import Modal from './Modal';

interface Props {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  pending?: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

const ConfirmModal = ({ open, title, message, confirmLabel, pending, onClose, onConfirm }: Props) => (
  <Modal open={open} onClose={pending ? () => undefined : onClose} title={title}>
    <div className="space-y-4">
      <p className="text-slate-200">{message}</p>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" disabled={pending} onClick={onClose}>
          Cancel
        </Button>
        <Button type="button" variant="danger" disabled={pending} onClick={onConfirm}>
          {confirmLabel}
        </Button>
      </div>
    </div>
  </Modal>
);

export default ConfirmModal;
