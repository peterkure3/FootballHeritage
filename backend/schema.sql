--
-- PostgreSQL database dump
--

\restrict 3l6yl3HjY9rde7OkPibaDSkIVbNMz1hrHEXfFeascdaocPUy5y2NJ6vaPGXHq5U

-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: log_admin_action(uuid, character varying, character varying, uuid, jsonb, character varying, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.log_admin_action(p_admin_id uuid, p_action character varying, p_target_type character varying DEFAULT NULL::character varying, p_target_id uuid DEFAULT NULL::uuid, p_details jsonb DEFAULT NULL::jsonb, p_ip_address character varying DEFAULT NULL::character varying, p_user_agent text DEFAULT NULL::text) RETURNS uuid
    LANGUAGE plpgsql
    AS $$
DECLARE
    log_id UUID;
BEGIN
    INSERT INTO admin_logs (
        admin_id,
        action,
        target_type,
        target_id,
        details,
        ip_address,
        user_agent
    ) VALUES (
        p_admin_id,
        p_action,
        p_target_type,
        p_target_id,
        p_details,
        p_ip_address,
        p_user_agent
    )
    RETURNING id INTO log_id;
    
    RETURN log_id;
END;
$$;


--
-- Name: update_parlay_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_parlay_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_platform_metrics(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_platform_metrics() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    metric_date DATE := CURRENT_DATE;
BEGIN
    INSERT INTO platform_metrics (
        date,
        total_users,
        new_users,
        active_users,
        total_bets,
        total_bet_amount,
        total_payouts,
        platform_revenue,
        total_deposits,
        total_withdrawals
    )
    SELECT
        metric_date,
        (SELECT COUNT(*) FROM users WHERE is_active = true),
        (SELECT COUNT(*) FROM users WHERE DATE(created_at) = metric_date),
        (SELECT COUNT(DISTINCT user_id) FROM bets WHERE DATE(created_at) = metric_date),
        (SELECT COUNT(*) FROM bets WHERE DATE(created_at) = metric_date),
        (SELECT COALESCE(SUM(amount), 0) FROM bets WHERE DATE(created_at) = metric_date),
        (SELECT COALESCE(SUM(potential_win), 0) FROM bets WHERE status = 'WON' AND DATE(settled_at) = metric_date),
        (SELECT COALESCE(SUM(amount), 0) - COALESCE(SUM(potential_win), 0) 
         FROM bets 
         WHERE status IN ('WON', 'LOST') AND DATE(settled_at) = metric_date),
        (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE transaction_type = 'DEPOSIT' AND DATE(created_at) = metric_date),
        (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE transaction_type = 'WITHDRAWAL' AND DATE(created_at) = metric_date)
    ON CONFLICT (date) 
    DO UPDATE SET
        total_users = EXCLUDED.total_users,
        new_users = EXCLUDED.new_users,
        active_users = EXCLUDED.active_users,
        total_bets = EXCLUDED.total_bets,
        total_bet_amount = EXCLUDED.total_bet_amount,
        total_payouts = EXCLUDED.total_payouts,
        platform_revenue = EXCLUDED.platform_revenue,
        total_deposits = EXCLUDED.total_deposits,
        total_withdrawals = EXCLUDED.total_withdrawals,
        updated_at = CURRENT_TIMESTAMP;
END;
$$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: _sqlx_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public._sqlx_migrations (
    version bigint NOT NULL,
    description text NOT NULL,
    installed_on timestamp with time zone DEFAULT now() NOT NULL,
    success boolean NOT NULL,
    checksum bytea NOT NULL,
    execution_time bigint NOT NULL
);


--
-- Name: bets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bets (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    event_id uuid NOT NULL,
    bet_type character varying(20) NOT NULL,
    selection character varying(10) NOT NULL,
    odds numeric(6,2) NOT NULL,
    amount numeric(15,2) NOT NULL,
    potential_win numeric(15,2) NOT NULL,
    status character varying(20) DEFAULT 'PENDING'::character varying,
    settled_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    settled_by uuid,
    CONSTRAINT bets_amount_check CHECK ((amount > (0)::numeric)),
    CONSTRAINT bets_bet_type_check CHECK (((bet_type)::text = ANY ((ARRAY['MONEYLINE'::character varying, 'SPREAD'::character varying, 'TOTAL'::character varying])::text[]))),
    CONSTRAINT bets_selection_check CHECK (((selection)::text = ANY ((ARRAY['HOME'::character varying, 'AWAY'::character varying, 'OVER'::character varying, 'UNDER'::character varying])::text[]))),
    CONSTRAINT bets_status_check CHECK (((status)::text = ANY ((ARRAY['PENDING'::character varying, 'WON'::character varying, 'LOST'::character varying, 'PUSH'::character varying, 'CANCELLED'::character varying])::text[])))
);


--
-- Name: events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.events (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    sport character varying(50) NOT NULL,
    league character varying(100) NOT NULL,
    home_team character varying(100) NOT NULL,
    away_team character varying(100) NOT NULL,
    event_date timestamp with time zone NOT NULL,
    status character varying(20) DEFAULT 'UPCOMING'::character varying,
    home_score integer,
    away_score integer,
    moneyline_home numeric(6,2),
    moneyline_away numeric(6,2),
    point_spread numeric(5,1),
    spread_home_odds numeric(6,2),
    spread_away_odds numeric(6,2),
    total_points numeric(5,1),
    over_odds numeric(6,2),
    under_odds numeric(6,2),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    created_by uuid,
    updated_by uuid,
    settled_by uuid,
    settled_at timestamp with time zone,
    external_id character varying(255),
    external_source character varying(50),
    CONSTRAINT events_status_check CHECK (((status)::text = ANY ((ARRAY['UPCOMING'::character varying, 'LIVE'::character varying, 'FINISHED'::character varying, 'CANCELLED'::character varying])::text[])))
);


--
-- Name: COLUMN events.league; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.events.league IS 'League or competition name (e.g., nba, nba_cup, nfl, premier_league)';


--
-- Name: fraud_alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fraud_alerts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid,
    alert_type character varying(50) NOT NULL,
    severity character varying(20) NOT NULL,
    description text NOT NULL,
    metadata jsonb,
    status character varying(20) DEFAULT 'pending'::character varying,
    reviewed_by uuid,
    reviewed_at timestamp with time zone,
    notes text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fraud_alerts_severity_check CHECK (((severity)::text = ANY ((ARRAY['low'::character varying, 'medium'::character varying, 'high'::character varying, 'critical'::character varying])::text[]))),
    CONSTRAINT fraud_alerts_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'investigating'::character varying, 'resolved'::character varying, 'false_positive'::character varying])::text[])))
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    first_name character varying(100) NOT NULL,
    last_name character varying(100) NOT NULL,
    date_of_birth date NOT NULL,
    phone character varying(20),
    address text,
    is_verified boolean DEFAULT false,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    last_login timestamp with time zone,
    login_count integer DEFAULT 0,
    failed_login_attempts integer DEFAULT 0,
    locked_until timestamp with time zone,
    role character varying(20) DEFAULT 'user'::character varying,
    CONSTRAINT check_age CHECK ((EXTRACT(year FROM age((CURRENT_DATE)::timestamp with time zone, (date_of_birth)::timestamp with time zone)) >= (21)::numeric)),
    CONSTRAINT users_role_check CHECK (((role)::text = ANY ((ARRAY['user'::character varying, 'admin'::character varying, 'superadmin'::character varying])::text[])))
);


--
-- Name: admin_dashboard_summary; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.admin_dashboard_summary AS
 SELECT ( SELECT count(*) AS count
           FROM public.users
          WHERE (users.is_active = true)) AS total_active_users,
    ( SELECT count(*) AS count
           FROM public.users
          WHERE (date(users.created_at) = CURRENT_DATE)) AS new_users_today,
    ( SELECT count(DISTINCT bets.user_id) AS count
           FROM public.bets
          WHERE (date(bets.created_at) = CURRENT_DATE)) AS active_users_today,
    ( SELECT count(*) AS count
           FROM public.bets
          WHERE (date(bets.created_at) = CURRENT_DATE)) AS bets_today,
    ( SELECT COALESCE(sum(bets.amount), (0)::numeric) AS "coalesce"
           FROM public.bets
          WHERE (date(bets.created_at) = CURRENT_DATE)) AS bet_volume_today,
    ( SELECT count(*) AS count
           FROM public.bets
          WHERE ((bets.status)::text = 'PENDING'::text)) AS pending_bets,
    ( SELECT (COALESCE(sum(bets.amount), (0)::numeric) - COALESCE(sum(bets.potential_win), (0)::numeric))
           FROM public.bets
          WHERE (((bets.status)::text = ANY ((ARRAY['WON'::character varying, 'LOST'::character varying])::text[])) AND (date(bets.settled_at) = CURRENT_DATE))) AS revenue_today,
    ( SELECT count(*) AS count
           FROM public.events
          WHERE ((events.status)::text = 'LIVE'::text)) AS live_events,
    ( SELECT count(*) AS count
           FROM public.events
          WHERE (((events.status)::text = 'UPCOMING'::text) AND (events.event_date > CURRENT_TIMESTAMP))) AS upcoming_events,
    ( SELECT count(*) AS count
           FROM public.fraud_alerts
          WHERE ((fraud_alerts.status)::text = 'pending'::text)) AS pending_alerts,
    ( SELECT count(*) AS count
           FROM public.fraud_alerts
          WHERE (((fraud_alerts.status)::text = 'pending'::text) AND ((fraud_alerts.severity)::text = ANY ((ARRAY['high'::character varying, 'critical'::character varying])::text[])))) AS critical_alerts;


--
-- Name: admin_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_logs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    admin_id uuid NOT NULL,
    action character varying(100) NOT NULL,
    target_type character varying(50),
    target_id uuid,
    details jsonb,
    ip_address character varying(45),
    user_agent text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: arbitrage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.arbitrage (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    event_id uuid,
    pipeline_match_id text,
    market text DEFAULT 'h2h'::text NOT NULL,
    selection_a text NOT NULL,
    selection_b text NOT NULL,
    book_a text NOT NULL,
    book_b text NOT NULL,
    odds_a double precision NOT NULL,
    odds_b double precision NOT NULL,
    arb_percentage double precision NOT NULL,
    total_stake numeric(15,2) NOT NULL,
    stake_a numeric(15,2) NOT NULL,
    stake_b numeric(15,2) NOT NULL,
    source_updated_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT arbitrage_stake_a_check CHECK ((stake_a > (0)::numeric)),
    CONSTRAINT arbitrage_stake_b_check CHECK ((stake_b > (0)::numeric)),
    CONSTRAINT arbitrage_total_stake_check CHECK ((total_stake > (0)::numeric))
);


--
-- Name: backtest_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.backtest_results (
    id integer NOT NULL,
    model_name character varying(100) NOT NULL,
    start_date timestamp without time zone,
    end_date timestamp without time zone,
    total_predictions integer,
    brier_score double precision,
    log_loss double precision,
    accuracy double precision,
    roi_flat_stake double precision,
    roi_kelly double precision,
    details jsonb,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: backtest_results_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.backtest_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: backtest_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.backtest_results_id_seq OWNED BY public.backtest_results.id;


--
-- Name: betting_patterns; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.betting_patterns (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    pattern_type character varying(50) NOT NULL,
    pattern_data jsonb NOT NULL,
    detected_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    is_flagged boolean DEFAULT false,
    reviewed_by uuid,
    review_notes text
);


--
-- Name: devigged_odds; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.devigged_odds (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    event_id uuid,
    pipeline_match_id text,
    bookmaker text NOT NULL,
    market text DEFAULT 'h2h'::text NOT NULL,
    outcome_a text NOT NULL,
    outcome_b text NOT NULL,
    odds_a double precision NOT NULL,
    odds_b double precision NOT NULL,
    fair_prob_a double precision NOT NULL,
    fair_prob_b double precision NOT NULL,
    vig double precision NOT NULL,
    source_updated_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT devigged_odds_fair_prob_a_check CHECK (((fair_prob_a >= (0)::double precision) AND (fair_prob_a <= (1)::double precision))),
    CONSTRAINT devigged_odds_fair_prob_b_check CHECK (((fair_prob_b >= (0)::double precision) AND (fair_prob_b <= (1)::double precision)))
);


--
-- Name: devigged_odds_archive; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.devigged_odds_archive (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    original_id uuid,
    event_id uuid,
    pipeline_match_id text,
    bookmaker text NOT NULL,
    market text DEFAULT 'h2h'::text NOT NULL,
    outcome_a text NOT NULL,
    outcome_b text NOT NULL,
    odds_a double precision NOT NULL,
    odds_b double precision NOT NULL,
    fair_prob_a double precision NOT NULL,
    fair_prob_b double precision NOT NULL,
    vig double precision NOT NULL,
    source_updated_at timestamp with time zone,
    original_created_at timestamp with time zone,
    archived_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: ev_bets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ev_bets (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    event_id uuid,
    pipeline_match_id text,
    bookmaker text,
    market text NOT NULL,
    selection text NOT NULL,
    odds double precision NOT NULL,
    stake numeric(15,2) NOT NULL,
    true_probability double precision NOT NULL,
    expected_value double precision NOT NULL,
    expected_value_pct double precision NOT NULL,
    source_updated_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ev_bets_stake_check CHECK ((stake > (0)::numeric)),
    CONSTRAINT ev_bets_true_probability_check CHECK (((true_probability >= (0)::double precision) AND (true_probability <= (1)::double precision)))
);


--
-- Name: gambling_limits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gambling_limits (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    daily_loss_limit numeric(15,2),
    weekly_loss_limit numeric(15,2),
    monthly_loss_limit numeric(15,2),
    daily_bet_limit numeric(15,2),
    weekly_bet_limit numeric(15,2),
    monthly_bet_limit numeric(15,2),
    max_single_bet numeric(15,2),
    session_time_limit integer,
    self_exclusion_until timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: nba_cup_upcoming_games; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.nba_cup_upcoming_games AS
 SELECT id,
    sport,
    league,
    home_team,
    away_team,
    event_date,
    status,
    home_score,
    away_score,
    moneyline_home,
    moneyline_away,
    point_spread,
    spread_home_odds,
    spread_away_odds,
    total_points,
    over_odds,
    under_odds,
    created_at,
    updated_at
   FROM public.events
  WHERE (((league)::text = 'nba_cup'::text) AND (event_date > now()))
  ORDER BY event_date;


--
-- Name: VIEW nba_cup_upcoming_games; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.nba_cup_upcoming_games IS 'Upcoming NBA Cup games with betting odds';


--
-- Name: odds_offers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.odds_offers (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    provider text NOT NULL,
    provider_event_id text NOT NULL,
    event_id uuid,
    book_key text NOT NULL,
    market text NOT NULL,
    selection text NOT NULL,
    line double precision,
    participant text,
    odds_decimal double precision NOT NULL,
    source_updated_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT odds_offers_odds_decimal_check CHECK ((odds_decimal > (1.0)::double precision))
);


--
-- Name: parlay_calculations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parlay_calculations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    num_legs integer NOT NULL,
    total_stake numeric(15,2) NOT NULL,
    combined_odds numeric(10,2) NOT NULL,
    combined_probability numeric(5,4) NOT NULL,
    expected_value numeric(15,2) NOT NULL,
    expected_profit numeric(15,2) NOT NULL,
    potential_payout numeric(15,2) NOT NULL,
    break_even_probability numeric(5,4) NOT NULL,
    kelly_criterion numeric(5,4),
    risk_level character varying(20) NOT NULL,
    recommendation text NOT NULL,
    calculation_data jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT parlay_calculations_num_legs_check CHECK ((num_legs > 0))
);


--
-- Name: TABLE parlay_calculations; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.parlay_calculations IS 'History of all parlay calculations for analytics';


--
-- Name: COLUMN parlay_calculations.kelly_criterion; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.parlay_calculations.kelly_criterion IS 'Kelly Criterion suggested stake percentage (0-0.25)';


--
-- Name: parlay_correlation_warnings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parlay_correlation_warnings (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    parlay_id uuid NOT NULL,
    leg_a_id uuid NOT NULL,
    leg_b_id uuid NOT NULL,
    severity character varying(20) NOT NULL,
    reason text NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT parlay_correlation_warnings_severity_check CHECK (((severity)::text = ANY ((ARRAY['LOW'::character varying, 'MEDIUM'::character varying, 'HIGH'::character varying])::text[])))
);


--
-- Name: TABLE parlay_correlation_warnings; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.parlay_correlation_warnings IS 'Correlation warnings between pairs of legs in a parlay';


--
-- Name: parlay_legs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parlay_legs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    parlay_id uuid NOT NULL,
    event_id uuid NOT NULL,
    team_name character varying(100) NOT NULL,
    bet_type character varying(20) NOT NULL,
    selection character varying(10) NOT NULL,
    odds numeric(6,2) NOT NULL,
    win_probability numeric(5,4),
    leg_order integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT parlay_legs_bet_type_check CHECK (((bet_type)::text = ANY ((ARRAY['MONEYLINE'::character varying, 'SPREAD'::character varying, 'TOTAL'::character varying])::text[]))),
    CONSTRAINT parlay_legs_selection_check CHECK (((selection)::text = ANY ((ARRAY['HOME'::character varying, 'AWAY'::character varying, 'OVER'::character varying, 'UNDER'::character varying])::text[]))),
    CONSTRAINT parlay_legs_win_probability_check CHECK (((win_probability >= (0)::numeric) AND (win_probability <= (1)::numeric)))
);


--
-- Name: TABLE parlay_legs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.parlay_legs IS 'Individual bets that make up a parlay';


--
-- Name: parlay_system_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parlay_system_results (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    parlay_id uuid NOT NULL,
    combination_number integer NOT NULL,
    leg_ids uuid[] NOT NULL,
    combined_odds numeric(10,2) NOT NULL,
    combined_probability numeric(5,4),
    potential_payout numeric(15,2),
    is_winning boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE parlay_system_results; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.parlay_system_results IS 'Individual combination results for system bets';


--
-- Name: parlays; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parlays (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    name character varying(100),
    total_stake numeric(15,2) NOT NULL,
    combined_odds numeric(10,2) NOT NULL,
    combined_probability numeric(5,4) NOT NULL,
    expected_value numeric(15,2) NOT NULL,
    potential_payout numeric(15,2) NOT NULL,
    risk_level character varying(20) NOT NULL,
    status character varying(20) DEFAULT 'DRAFT'::character varying,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    parlay_type character varying(20) DEFAULT 'STANDARD'::character varying,
    system_min_legs integer,
    total_combinations integer,
    combined_edge numeric(10,4),
    correlation_score numeric(5,4) DEFAULT 0,
    CONSTRAINT parlays_combined_probability_check CHECK (((combined_probability >= (0)::numeric) AND (combined_probability <= (1)::numeric))),
    CONSTRAINT parlays_parlay_type_check CHECK (((parlay_type)::text = ANY ((ARRAY['STANDARD'::character varying, 'SYSTEM_2_3'::character varying, 'SYSTEM_3_4'::character varying, 'SYSTEM_2_4'::character varying, 'SYSTEM_3_5'::character varying, 'TEASER'::character varying, 'PLEASER'::character varying])::text[]))),
    CONSTRAINT parlays_risk_level_check CHECK (((risk_level)::text = ANY ((ARRAY['LOW'::character varying, 'MEDIUM'::character varying, 'HIGH'::character varying, 'VERY_HIGH'::character varying])::text[]))),
    CONSTRAINT parlays_status_check CHECK (((status)::text = ANY ((ARRAY['DRAFT'::character varying, 'ACTIVE'::character varying, 'WON'::character varying, 'LOST'::character varying, 'PUSH'::character varying, 'CANCELLED'::character varying])::text[]))),
    CONSTRAINT parlays_system_min_legs_check CHECK (((system_min_legs IS NULL) OR (system_min_legs > 0))),
    CONSTRAINT parlays_total_stake_check CHECK ((total_stake > (0)::numeric))
);


--
-- Name: TABLE parlays; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.parlays IS 'Stores saved parlay combinations with EV calculations';


--
-- Name: COLUMN parlays.combined_odds; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.parlays.combined_odds IS 'Product of all individual bet odds';


--
-- Name: COLUMN parlays.combined_probability; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.parlays.combined_probability IS 'Product of all individual win probabilities';


--
-- Name: COLUMN parlays.expected_value; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.parlays.expected_value IS 'Expected value as percentage of stake';


--
-- Name: COLUMN parlays.parlay_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.parlays.parlay_type IS 'Type of parlay: STANDARD, SYSTEM_N_M (N of M must win), TEASER, PLEASER';


--
-- Name: COLUMN parlays.system_min_legs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.parlays.system_min_legs IS 'For system bets: minimum number of legs that must win';


--
-- Name: COLUMN parlays.correlation_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.parlays.correlation_score IS '0-1 score where higher means more correlated bets';


--
-- Name: platform_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.platform_metrics (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    date date NOT NULL,
    total_users integer DEFAULT 0,
    new_users integer DEFAULT 0,
    active_users integer DEFAULT 0,
    total_bets integer DEFAULT 0,
    total_bet_amount numeric(15,2) DEFAULT 0,
    total_payouts numeric(15,2) DEFAULT 0,
    platform_revenue numeric(15,2) DEFAULT 0,
    total_deposits numeric(15,2) DEFAULT 0,
    total_withdrawals numeric(15,2) DEFAULT 0,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: player_props; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.player_props (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    event_id uuid NOT NULL,
    sport character varying(50) NOT NULL,
    league character varying(50) NOT NULL,
    player_name character varying(100) NOT NULL,
    team character varying(100),
    market character varying(50) NOT NULL,
    line numeric(10,2) NOT NULL,
    over_odds numeric(10,2),
    under_odds numeric(10,2),
    source character varying(50) DEFAULT 'the_odds_api'::character varying,
    source_updated_at timestamp with time zone,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: provider_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.provider_events (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    provider text NOT NULL,
    provider_event_id text NOT NULL,
    sport character varying(50),
    league character varying(100),
    home_team text,
    away_team text,
    commence_time timestamp with time zone,
    event_id uuid,
    source_updated_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: sportsbook_registry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sportsbook_registry (
    book_key text NOT NULL,
    display_name text NOT NULL,
    provider text DEFAULT 'oddsapi'::text NOT NULL,
    provider_book_key text NOT NULL,
    region text NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    supports_sports jsonb DEFAULT '[]'::jsonb NOT NULL,
    supports_markets jsonb DEFAULT '[]'::jsonb NOT NULL,
    is_sharp_reference boolean DEFAULT false NOT NULL,
    priority integer DEFAULT 100 NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT sportsbook_registry_region_check CHECK ((region = ANY (ARRAY['us'::text, 'eu'::text, 'uk'::text, 'au'::text, 'global'::text])))
);


--
-- Name: team_elo_ratings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.team_elo_ratings (
    id integer NOT NULL,
    team_name character varying(255) NOT NULL,
    elo double precision NOT NULL,
    form_score double precision DEFAULT 0,
    games_played integer DEFAULT 0,
    recent_results character varying(10),
    updated_at timestamp without time zone DEFAULT now()
);


--
-- Name: team_elo_ratings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.team_elo_ratings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: team_elo_ratings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.team_elo_ratings_id_seq OWNED BY public.team_elo_ratings.id;


--
-- Name: transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.transactions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    wallet_id uuid NOT NULL,
    transaction_type character varying(20) NOT NULL,
    amount numeric(15,2) NOT NULL,
    balance_before numeric(15,2) NOT NULL,
    balance_after numeric(15,2) NOT NULL,
    description text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    is_fraud_flagged boolean DEFAULT false,
    status character varying(20) DEFAULT 'completed'::character varying NOT NULL,
    CONSTRAINT transactions_amount_check CHECK ((amount > (0)::numeric)),
    CONSTRAINT transactions_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'completed'::character varying, 'failed'::character varying, 'cancelled'::character varying])::text[]))),
    CONSTRAINT transactions_transaction_type_check CHECK (((transaction_type)::text = ANY ((ARRAY['DEPOSIT'::character varying, 'WITHDRAWAL'::character varying, 'BET_PLACED'::character varying, 'BET_WON'::character varying, 'BET_LOST'::character varying])::text[])))
);


--
-- Name: user_activity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_activity (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    activity_type character varying(50) NOT NULL,
    ip_address inet,
    user_agent text,
    "timestamp" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    metadata jsonb,
    is_suspicious boolean DEFAULT false
);


--
-- Name: wallets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wallets (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    encrypted_balance text NOT NULL,
    encryption_iv text NOT NULL,
    total_deposits numeric(15,2) DEFAULT 0.00,
    total_withdrawals numeric(15,2) DEFAULT 0.00,
    total_winnings numeric(15,2) DEFAULT 0.00,
    total_losses numeric(15,2) DEFAULT 0.00,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_encrypted_balance_not_empty CHECK (((encrypted_balance IS NOT NULL) AND (encrypted_balance <> ''::text)))
);


--
-- Name: backtest_results id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backtest_results ALTER COLUMN id SET DEFAULT nextval('public.backtest_results_id_seq'::regclass);


--
-- Name: team_elo_ratings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_elo_ratings ALTER COLUMN id SET DEFAULT nextval('public.team_elo_ratings_id_seq'::regclass);


--
-- Name: _sqlx_migrations _sqlx_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public._sqlx_migrations
    ADD CONSTRAINT _sqlx_migrations_pkey PRIMARY KEY (version);


--
-- Name: admin_logs admin_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_logs
    ADD CONSTRAINT admin_logs_pkey PRIMARY KEY (id);


--
-- Name: arbitrage arbitrage_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.arbitrage
    ADD CONSTRAINT arbitrage_pkey PRIMARY KEY (id);


--
-- Name: backtest_results backtest_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backtest_results
    ADD CONSTRAINT backtest_results_pkey PRIMARY KEY (id);


--
-- Name: bets bets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bets
    ADD CONSTRAINT bets_pkey PRIMARY KEY (id);


--
-- Name: betting_patterns betting_patterns_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.betting_patterns
    ADD CONSTRAINT betting_patterns_pkey PRIMARY KEY (id);


--
-- Name: devigged_odds_archive devigged_odds_archive_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devigged_odds_archive
    ADD CONSTRAINT devigged_odds_archive_pkey PRIMARY KEY (id);


--
-- Name: devigged_odds devigged_odds_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devigged_odds
    ADD CONSTRAINT devigged_odds_pkey PRIMARY KEY (id);


--
-- Name: ev_bets ev_bets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ev_bets
    ADD CONSTRAINT ev_bets_pkey PRIMARY KEY (id);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: fraud_alerts fraud_alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fraud_alerts
    ADD CONSTRAINT fraud_alerts_pkey PRIMARY KEY (id);


--
-- Name: gambling_limits gambling_limits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gambling_limits
    ADD CONSTRAINT gambling_limits_pkey PRIMARY KEY (id);


--
-- Name: odds_offers odds_offers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.odds_offers
    ADD CONSTRAINT odds_offers_pkey PRIMARY KEY (id);


--
-- Name: parlay_calculations parlay_calculations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parlay_calculations
    ADD CONSTRAINT parlay_calculations_pkey PRIMARY KEY (id);


--
-- Name: parlay_correlation_warnings parlay_correlation_warnings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parlay_correlation_warnings
    ADD CONSTRAINT parlay_correlation_warnings_pkey PRIMARY KEY (id);


--
-- Name: parlay_legs parlay_legs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parlay_legs
    ADD CONSTRAINT parlay_legs_pkey PRIMARY KEY (id);


--
-- Name: parlay_system_results parlay_system_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parlay_system_results
    ADD CONSTRAINT parlay_system_results_pkey PRIMARY KEY (id);


--
-- Name: parlays parlays_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parlays
    ADD CONSTRAINT parlays_pkey PRIMARY KEY (id);


--
-- Name: platform_metrics platform_metrics_date_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_metrics
    ADD CONSTRAINT platform_metrics_date_key UNIQUE (date);


--
-- Name: platform_metrics platform_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platform_metrics
    ADD CONSTRAINT platform_metrics_pkey PRIMARY KEY (id);


--
-- Name: player_props player_props_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_props
    ADD CONSTRAINT player_props_pkey PRIMARY KEY (id);


--
-- Name: provider_events provider_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.provider_events
    ADD CONSTRAINT provider_events_pkey PRIMARY KEY (id);


--
-- Name: sportsbook_registry sportsbook_registry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sportsbook_registry
    ADD CONSTRAINT sportsbook_registry_pkey PRIMARY KEY (book_key);


--
-- Name: team_elo_ratings team_elo_ratings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_elo_ratings
    ADD CONSTRAINT team_elo_ratings_pkey PRIMARY KEY (id);


--
-- Name: team_elo_ratings team_elo_ratings_team_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.team_elo_ratings
    ADD CONSTRAINT team_elo_ratings_team_name_key UNIQUE (team_name);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: user_activity user_activity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_activity
    ADD CONSTRAINT user_activity_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: wallets wallets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_pkey PRIMARY KEY (id);


--
-- Name: idx_admin_logs_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_admin_logs_action ON public.admin_logs USING btree (action);


--
-- Name: idx_admin_logs_admin_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_admin_logs_admin_id ON public.admin_logs USING btree (admin_id);


--
-- Name: idx_admin_logs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_admin_logs_created_at ON public.admin_logs USING btree (created_at DESC);


--
-- Name: idx_admin_logs_target; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_admin_logs_target ON public.admin_logs USING btree (target_type, target_id);


--
-- Name: idx_arbitrage_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_arbitrage_created_at ON public.arbitrage USING btree (created_at DESC);


--
-- Name: idx_arbitrage_edge; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_arbitrage_edge ON public.arbitrage USING btree (arb_percentage DESC);


--
-- Name: idx_arbitrage_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_arbitrage_event_id ON public.arbitrage USING btree (event_id);


--
-- Name: idx_arbitrage_market; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_arbitrage_market ON public.arbitrage USING btree (market);


--
-- Name: idx_arbitrage_pipeline_match_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_arbitrage_pipeline_match_id ON public.arbitrage USING btree (pipeline_match_id);


--
-- Name: idx_bets_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bets_created_at ON public.bets USING btree (created_at);


--
-- Name: idx_bets_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bets_event_id ON public.bets USING btree (event_id);


--
-- Name: idx_bets_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bets_status ON public.bets USING btree (status);


--
-- Name: idx_bets_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bets_user_id ON public.bets USING btree (user_id);


--
-- Name: idx_devigged_archive_archived_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_devigged_archive_archived_at ON public.devigged_odds_archive USING btree (archived_at DESC);


--
-- Name: idx_devigged_archive_bookmaker; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_devigged_archive_bookmaker ON public.devigged_odds_archive USING btree (bookmaker);


--
-- Name: idx_devigged_archive_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_devigged_archive_event_id ON public.devigged_odds_archive USING btree (event_id);


--
-- Name: idx_devigged_archive_pipeline_match_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_devigged_archive_pipeline_match_id ON public.devigged_odds_archive USING btree (pipeline_match_id);


--
-- Name: idx_devigged_archive_source_updated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_devigged_archive_source_updated ON public.devigged_odds_archive USING btree (source_updated_at);


--
-- Name: idx_devigged_odds_book_market; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_devigged_odds_book_market ON public.devigged_odds USING btree (bookmaker, market);


--
-- Name: idx_devigged_odds_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_devigged_odds_created_at ON public.devigged_odds USING btree (created_at DESC);


--
-- Name: idx_devigged_odds_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_devigged_odds_event_id ON public.devigged_odds USING btree (event_id);


--
-- Name: idx_devigged_odds_pipeline_match_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_devigged_odds_pipeline_match_id ON public.devigged_odds USING btree (pipeline_match_id);


--
-- Name: idx_ev_bets_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ev_bets_created_at ON public.ev_bets USING btree (created_at DESC);


--
-- Name: idx_ev_bets_ev_pct; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ev_bets_ev_pct ON public.ev_bets USING btree (expected_value_pct DESC);


--
-- Name: idx_ev_bets_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ev_bets_event_id ON public.ev_bets USING btree (event_id);


--
-- Name: idx_ev_bets_market; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ev_bets_market ON public.ev_bets USING btree (market);


--
-- Name: idx_ev_bets_pipeline_match_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ev_bets_pipeline_match_id ON public.ev_bets USING btree (pipeline_match_id);


--
-- Name: idx_events_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_date ON public.events USING btree (event_date);


--
-- Name: idx_events_event_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_event_date ON public.events USING btree (event_date DESC);


--
-- Name: idx_events_external; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_events_external ON public.events USING btree (external_id, external_source) WHERE ((external_id IS NOT NULL) AND (external_source IS NOT NULL));


--
-- Name: idx_events_league_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_league_date ON public.events USING btree (league, event_date);


--
-- Name: idx_events_sport; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_sport ON public.events USING btree (sport);


--
-- Name: idx_events_sport_event_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_sport_event_date ON public.events USING btree (sport, event_date DESC);


--
-- Name: idx_events_sport_league; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_sport_league ON public.events USING btree (sport, league);


--
-- Name: idx_events_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_status ON public.events USING btree (status);


--
-- Name: idx_events_status_event_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_status_event_date ON public.events USING btree (status, event_date DESC);


--
-- Name: idx_fraud_alerts_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fraud_alerts_created_at ON public.fraud_alerts USING btree (created_at DESC);


--
-- Name: idx_fraud_alerts_severity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fraud_alerts_severity ON public.fraud_alerts USING btree (severity);


--
-- Name: idx_fraud_alerts_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fraud_alerts_status ON public.fraud_alerts USING btree (status);


--
-- Name: idx_fraud_alerts_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fraud_alerts_user_id ON public.fraud_alerts USING btree (user_id);


--
-- Name: idx_gambling_limits_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gambling_limits_user_id ON public.gambling_limits USING btree (user_id);


--
-- Name: idx_odds_offers_book_market; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_odds_offers_book_market ON public.odds_offers USING btree (book_key, market);


--
-- Name: idx_odds_offers_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_odds_offers_created_at ON public.odds_offers USING btree (created_at DESC);


--
-- Name: idx_odds_offers_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_odds_offers_event_id ON public.odds_offers USING btree (event_id);


--
-- Name: idx_odds_offers_provider_event; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_odds_offers_provider_event ON public.odds_offers USING btree (provider, provider_event_id);


--
-- Name: idx_parlay_calculations_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parlay_calculations_created_at ON public.parlay_calculations USING btree (created_at DESC);


--
-- Name: idx_parlay_calculations_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parlay_calculations_user_id ON public.parlay_calculations USING btree (user_id);


--
-- Name: idx_parlay_correlation_parlay; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parlay_correlation_parlay ON public.parlay_correlation_warnings USING btree (parlay_id);


--
-- Name: idx_parlay_legs_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parlay_legs_event_id ON public.parlay_legs USING btree (event_id);


--
-- Name: idx_parlay_legs_parlay_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parlay_legs_parlay_id ON public.parlay_legs USING btree (parlay_id);


--
-- Name: idx_parlay_system_parlay; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parlay_system_parlay ON public.parlay_system_results USING btree (parlay_id);


--
-- Name: idx_parlays_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parlays_created_at ON public.parlays USING btree (created_at DESC);


--
-- Name: idx_parlays_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parlays_status ON public.parlays USING btree (status);


--
-- Name: idx_parlays_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parlays_user_id ON public.parlays USING btree (user_id);


--
-- Name: idx_platform_metrics_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_platform_metrics_date ON public.platform_metrics USING btree (date DESC);


--
-- Name: idx_player_props_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_player_props_active ON public.player_props USING btree (event_id, is_active) WHERE (is_active = true);


--
-- Name: idx_player_props_event; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_player_props_event ON public.player_props USING btree (event_id);


--
-- Name: idx_player_props_market; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_player_props_market ON public.player_props USING btree (sport, market);


--
-- Name: idx_player_props_player; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_player_props_player ON public.player_props USING btree (player_name);


--
-- Name: idx_provider_events_commence_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_provider_events_commence_time ON public.provider_events USING btree (commence_time);


--
-- Name: idx_provider_events_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_provider_events_event_id ON public.provider_events USING btree (event_id);


--
-- Name: idx_sportsbook_registry_enabled_region; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sportsbook_registry_enabled_region ON public.sportsbook_registry USING btree (enabled, region);


--
-- Name: idx_sportsbook_registry_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sportsbook_registry_priority ON public.sportsbook_registry USING btree (priority);


--
-- Name: idx_sportsbook_registry_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sportsbook_registry_provider ON public.sportsbook_registry USING btree (provider, provider_book_key);


--
-- Name: idx_transactions_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transactions_created_at ON public.transactions USING btree (created_at);


--
-- Name: idx_transactions_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transactions_type ON public.transactions USING btree (transaction_type);


--
-- Name: idx_transactions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transactions_user_id ON public.transactions USING btree (user_id);


--
-- Name: idx_user_activity_ip; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_activity_ip ON public.user_activity USING btree (ip_address);


--
-- Name: idx_user_activity_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_activity_timestamp ON public.user_activity USING btree ("timestamp");


--
-- Name: idx_user_activity_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_activity_user_id ON public.user_activity USING btree (user_id);


--
-- Name: idx_users_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_created_at ON public.users USING btree (created_at);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_role ON public.users USING btree (role);


--
-- Name: idx_wallets_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wallets_user_id ON public.wallets USING btree (user_id);


--
-- Name: uq_arbitrage_snapshot; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_arbitrage_snapshot ON public.arbitrage USING btree (pipeline_match_id, market, selection_a, selection_b, book_a, book_b, odds_a, odds_b, total_stake, source_updated_at);


--
-- Name: uq_devigged_odds_snapshot; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_devigged_odds_snapshot ON public.devigged_odds USING btree (pipeline_match_id, bookmaker, market, outcome_a, outcome_b, odds_a, odds_b, source_updated_at);


--
-- Name: uq_ev_bets_snapshot; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_ev_bets_snapshot ON public.ev_bets USING btree (pipeline_match_id, bookmaker, market, selection, odds, stake, true_probability, source_updated_at);


--
-- Name: uq_odds_offers_snapshot; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_odds_offers_snapshot ON public.odds_offers USING btree (provider, provider_event_id, book_key, market, selection, line, participant, source_updated_at, odds_decimal);


--
-- Name: uq_provider_events; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_provider_events ON public.provider_events USING btree (provider, provider_event_id);


--
-- Name: parlays trigger_update_parlay_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_update_parlay_updated_at BEFORE UPDATE ON public.parlays FOR EACH ROW EXECUTE FUNCTION public.update_parlay_updated_at();


--
-- Name: bets update_bets_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_bets_updated_at BEFORE UPDATE ON public.bets FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: events update_events_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON public.events FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: gambling_limits update_gambling_limits_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_gambling_limits_updated_at BEFORE UPDATE ON public.gambling_limits FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: wallets update_wallets_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_wallets_updated_at BEFORE UPDATE ON public.wallets FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: admin_logs admin_logs_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_logs
    ADD CONSTRAINT admin_logs_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: arbitrage arbitrage_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.arbitrage
    ADD CONSTRAINT arbitrage_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: bets bets_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bets
    ADD CONSTRAINT bets_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: bets bets_settled_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bets
    ADD CONSTRAINT bets_settled_by_fkey FOREIGN KEY (settled_by) REFERENCES public.users(id);


--
-- Name: bets bets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bets
    ADD CONSTRAINT bets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: betting_patterns betting_patterns_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.betting_patterns
    ADD CONSTRAINT betting_patterns_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(id);


--
-- Name: betting_patterns betting_patterns_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.betting_patterns
    ADD CONSTRAINT betting_patterns_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: devigged_odds devigged_odds_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devigged_odds
    ADD CONSTRAINT devigged_odds_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: ev_bets ev_bets_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ev_bets
    ADD CONSTRAINT ev_bets_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: events events_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: events events_settled_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_settled_by_fkey FOREIGN KEY (settled_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: events events_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: fraud_alerts fraud_alerts_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fraud_alerts
    ADD CONSTRAINT fraud_alerts_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: fraud_alerts fraud_alerts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fraud_alerts
    ADD CONSTRAINT fraud_alerts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: gambling_limits gambling_limits_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gambling_limits
    ADD CONSTRAINT gambling_limits_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: odds_offers odds_offers_book_key_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.odds_offers
    ADD CONSTRAINT odds_offers_book_key_fkey FOREIGN KEY (book_key) REFERENCES public.sportsbook_registry(book_key) ON DELETE RESTRICT;


--
-- Name: odds_offers odds_offers_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.odds_offers
    ADD CONSTRAINT odds_offers_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE SET NULL;


--
-- Name: parlay_calculations parlay_calculations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parlay_calculations
    ADD CONSTRAINT parlay_calculations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: parlay_correlation_warnings parlay_correlation_warnings_leg_a_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parlay_correlation_warnings
    ADD CONSTRAINT parlay_correlation_warnings_leg_a_id_fkey FOREIGN KEY (leg_a_id) REFERENCES public.parlay_legs(id) ON DELETE CASCADE;


--
-- Name: parlay_correlation_warnings parlay_correlation_warnings_leg_b_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parlay_correlation_warnings
    ADD CONSTRAINT parlay_correlation_warnings_leg_b_id_fkey FOREIGN KEY (leg_b_id) REFERENCES public.parlay_legs(id) ON DELETE CASCADE;


--
-- Name: parlay_correlation_warnings parlay_correlation_warnings_parlay_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parlay_correlation_warnings
    ADD CONSTRAINT parlay_correlation_warnings_parlay_id_fkey FOREIGN KEY (parlay_id) REFERENCES public.parlays(id) ON DELETE CASCADE;


--
-- Name: parlay_legs parlay_legs_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parlay_legs
    ADD CONSTRAINT parlay_legs_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: parlay_legs parlay_legs_parlay_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parlay_legs
    ADD CONSTRAINT parlay_legs_parlay_id_fkey FOREIGN KEY (parlay_id) REFERENCES public.parlays(id) ON DELETE CASCADE;


--
-- Name: parlay_system_results parlay_system_results_parlay_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parlay_system_results
    ADD CONSTRAINT parlay_system_results_parlay_id_fkey FOREIGN KEY (parlay_id) REFERENCES public.parlays(id) ON DELETE CASCADE;


--
-- Name: parlays parlays_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parlays
    ADD CONSTRAINT parlays_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: player_props player_props_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_props
    ADD CONSTRAINT player_props_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: provider_events provider_events_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.provider_events
    ADD CONSTRAINT provider_events_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE SET NULL;


--
-- Name: transactions transactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: transactions transactions_wallet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_wallet_id_fkey FOREIGN KEY (wallet_id) REFERENCES public.wallets(id) ON DELETE CASCADE;


--
-- Name: user_activity user_activity_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_activity
    ADD CONSTRAINT user_activity_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: wallets wallets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 3l6yl3HjY9rde7OkPibaDSkIVbNMz1hrHEXfFeascdaocPUy5y2NJ6vaPGXHq5U

