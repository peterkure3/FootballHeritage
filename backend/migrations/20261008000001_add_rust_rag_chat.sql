ALTER TABLE ai_messages ADD COLUMN metadata JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE ai_messages ADD COLUMN sequence BIGSERIAL NOT NULL;
CREATE INDEX idx_ai_messages_sequence ON ai_messages(conversation_id, sequence);

CREATE TABLE ai_chat_requests (
    id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    request JSONB NOT NULL,
    response JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id,id)
);

CREATE TABLE ai_rag_documents (
    source_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', title), 'A') ||
        setweight(to_tsvector('english', content), 'B')
    ) STORED,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_ai_rag_documents_search ON ai_rag_documents USING GIN(search_vector);
INSERT INTO ai_rag_documents(source_id,title,content) VALUES
('footballheritage:probability','Understanding model probability',
 'Home win, draw and away win probabilities are estimated by the active statistical model and sum to one. The highest probability is the most likely outcome, not a guarantee. A high predicted probability alone does not demonstrate betting value. No current calibration or accuracy claim should be made without evaluation evidence.'),
('footballheritage:odds','Decimal odds and implied probability',
 'For observed decimal odds d greater than one, odds-implied probability is 1/d. This includes bookmaker margin. For a complete home/draw/away market, the margin is the sum of the three implied probabilities minus one. Without an observed bookmaker quote, odds-implied probability is unavailable.'),
('footballheritage:value','Edge and expected value',
 'Edge is model probability p minus odds-implied probability 1/d. Multiply by 100 to express edge in percentage points. Expected profit for one unit is p*d - 1. A positive estimate depends on the model being reliable. AI Picks labels a value comparison when a real recent quote gives at least five percentage points of edge. Missing quotes must never be replaced with invented odds.'),
('footballheritage:evidence','Prediction evidence and freshness',
 'AI Picks uses the latest active-model prediction created within 24 hours, for unfinished football fixtures in the next 30 days. Current bookmaker quotes must be no older than 24 hours and not future-dated. Fixture dates are interpreted in UTC. A model prediction can be shown without bookmaker odds; no edge or expected value can then be calculated.'),
('footballheritage:scope','Chat capabilities',
 'Chat explains retrieved football fixtures, model probabilities and odds concepts. It cannot place bets, read or modify wallets, execute payments or promise winnings. Predictions for other sports are unavailable through this football model. Injuries, news and final scores should only be described when supporting evidence has been retrieved.');
