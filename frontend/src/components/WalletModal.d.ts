import type { ComponentType } from "react";
declare const WalletModal: ComponentType<{
  isOpen: boolean;
  onClose: () => void;
  initialTab?: string;
  currentBalance?: number;
  restoreFocus?: () => HTMLElement | null;
}>;
export default WalletModal;
