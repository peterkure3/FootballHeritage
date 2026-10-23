-- Fail safely if legacy duplicate wallets need operator reconciliation; never
-- delete balances or choose an arbitrary duplicate during a release.
CREATE UNIQUE INDEX wallets_unique_user_id ON wallets(user_id);
