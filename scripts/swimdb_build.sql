--
-- PostgreSQL database dump
--

-- Dumped from database version 10.1
-- Dumped by pg_dump version 10.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- Name: top_swim_select(text, text, integer); Type: FUNCTION; Schema: public; Owner: hallmank
--

CREATE FUNCTION top_swim_select(gen text, div text, sea integer) RETURNS SETOF refcursor
    LANGUAGE plpgsql
    AS $$
	DECLARE
   		ref1 refcursor;
	BEGIN
	OPEN ref1 FOR SELECT event, time, rank, name, meet, team, year, swimmer_id, season, gender, division, date FROM 
		(SELECT swim.name, time, event, meet, swim.team, sw.year, swimmer_id, ts.season, sw.gender, ts.division, date, rank() 
		OVER (PARTITION BY swim.name, event, ts.id ORDER BY time, date) 
		FROM (swim 
			INNER JOIN swimmer sw ON swim.swimmer_id=sw.id
			INNER JOIN teamseason ts ON sw.team_id=ts.id) 
			WHERE ts.gender=gen and ts.division=div and ts.season=sea
		) AS a 
		WHERE a.rank=1;
		
      RETURN NEXT ref1;
    END;
    $$;


ALTER FUNCTION public.top_swim_select(gen text, div text, sea integer) OWNER TO hallmank;

--
-- Name: top_swim_select(text, text, text); Type: FUNCTION; Schema: public; Owner: hallmank
--

CREATE FUNCTION top_swim_select(gen text, div text, sea text) RETURNS SETOF refcursor
    LANGUAGE plpgsql
    AS $$
	DECLARE
   		ref1 refcursor;
	BEGIN
	OPEN ref1 FOR SELECT event, time, rank, name, meet, team, year, swimmer_id, season, gender, division, date FROM 
		(SELECT swim.name, time, event, meet, swim.team, sw.year, swimmer_id, ts.season, sw.gender, ts.division, date, rank() 
		OVER (PARTITION BY swim.name, event, ts.id ORDER BY time, date) 
		FROM (swim 
			INNER JOIN swimmer sw ON swim.swimmer_id=sw.id
			INNER JOIN teamseason ts ON sw.team_id=ts.id) 
			WHERE ts.gender=gen and ts.division=div and ts.season=sea
		) AS a 
		WHERE a.rank=1;
		
      RETURN NEXT ref1;
    END;
    $$;


ALTER FUNCTION public.top_swim_select(gen text, div text, sea text) OWNER TO hallmank;

--
-- Name: top_swim_select(text, text, text, text, text); Type: FUNCTION; Schema: public; Owner: hallmank
--

CREATE FUNCTION top_swim_select(gender text, division text, season text, conference text, asdate text) RETURNS SETOF refcursor
    LANGUAGE plpgsql
    AS $$
	DECLARE
   		ref1 refcursor;
	BEGIN
	OPEN ref1 FOR SELECT event, time, rank, name, meet, team, year, swimmer_id, season, gender, division, date FROM 
		(SELECT swim.name, time, event, meet, swim.team, sw.year, swimmer_id, ts.season, sw.gender, ts.division, date, rank() 
		OVER (PARTITION BY swim.name, event, ts.id ORDER BY time, date) 
		FROM (swim 
			INNER JOIN swimmer sw ON swim.swimmer_id=sw.id
			INNER JOIN teamseason ts ON sw.team_id=ts.id) 
			WHERE ts.gender=gender and ts.division=division and ts.season=season
		) AS a 
		WHERE a.rank=1;
		
      RETURN NEXT ref1;
    END;
    $$;


ALTER FUNCTION public.top_swim_select(gender text, division text, season text, conference text, asdate text) OWNER TO hallmank;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: clubswim; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE clubswim (
    id integer NOT NULL,
    swimmer_id integer NOT NULL,
    team_id integer NOT NULL,
    course character varying(255) NOT NULL,
    event character varying(255) NOT NULL,
    date date NOT NULL,
    "time" integer NOT NULL,
    meet character varying(255) NOT NULL,
    powerpoints integer
);


ALTER TABLE clubswim OWNER TO hallmank;

--
-- Name: clubswim_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE clubswim_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE clubswim_id_seq OWNER TO hallmank;

--
-- Name: clubswim_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE clubswim_id_seq OWNED BY clubswim.id;


--
-- Name: clubswimmer; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE clubswimmer (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    gender character varying(255) NOT NULL,
    relay boolean NOT NULL,
    age integer NOT NULL,
    team character varying(255) NOT NULL,
    ppts integer,
    eventppts character varying(255)
);


ALTER TABLE clubswimmer OWNER TO hallmank;

--
-- Name: clubswimmer_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE clubswimmer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE clubswimmer_id_seq OWNER TO hallmank;

--
-- Name: clubswimmer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE clubswimmer_id_seq OWNED BY clubswimmer.id;


--
-- Name: clubteam; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE clubteam (
    id integer NOT NULL,
    season integer NOT NULL,
    team character varying(255) NOT NULL,
    gender character varying(255) NOT NULL,
    winnats real,
    strengthdual real,
    strengthinvite real
);


ALTER TABLE clubteam OWNER TO hallmank;

--
-- Name: clubteam_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE clubteam_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE clubteam_id_seq OWNER TO hallmank;

--
-- Name: clubteam_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE clubteam_id_seq OWNED BY clubteam.id;


--
-- Name: clubtimedist; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE clubtimedist (
    id integer NOT NULL,
    event character varying(255) NOT NULL,
    gender character varying(255) NOT NULL,
    age integer NOT NULL,
    course character varying(255) NOT NULL,
    mu real NOT NULL,
    sigma real NOT NULL,
    a real,
    year integer
);


ALTER TABLE clubtimedist OWNER TO hallmank;

--
-- Name: clubtimedist_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE clubtimedist_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE clubtimedist_id_seq OWNER TO hallmank;

--
-- Name: clubtimedist_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE clubtimedist_id_seq OWNED BY clubtimedist.id;


--
-- Name: event; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE event (
    id integer NOT NULL,
    stroke character varying(255) NOT NULL,
    stroke_long character varying(255) NOT NULL,
    distance integer NOT NULL,
    course character varying(255) NOT NULL,
    relay boolean
);


ALTER TABLE event OWNER TO hallmank;

--
-- Name: event_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE event_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE event_id_seq OWNER TO hallmank;

--
-- Name: event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE event_id_seq OWNED BY event.id;


--
-- Name: fantasyconference; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE fantasyconference (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    gender character varying(255) NOT NULL,
    conference character varying(255),
    division character varying(255) NOT NULL,
    season integer NOT NULL,
    team_limit integer NOT NULL,
    team_size_limit integer NOT NULL
);


ALTER TABLE fantasyconference OWNER TO hallmank;

--
-- Name: fantasyconference_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE fantasyconference_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE fantasyconference_id_seq OWNER TO hallmank;

--
-- Name: fantasyconference_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE fantasyconference_id_seq OWNED BY fantasyconference.id;


--
-- Name: fantasyowner; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE fantasyowner (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    password character varying(255) NOT NULL
);


ALTER TABLE fantasyowner OWNER TO hallmank;

--
-- Name: fantasyowner_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE fantasyowner_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE fantasyowner_id_seq OWNER TO hallmank;

--
-- Name: fantasyowner_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE fantasyowner_id_seq OWNED BY fantasyowner.id;


--
-- Name: fantasyscore; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE fantasyscore (
    id integer NOT NULL,
    conference_id integer NOT NULL,
    team_one_id integer NOT NULL,
    team_one_score integer,
    team_two_id integer NOT NULL,
    team_two_score integer,
    week integer NOT NULL
);


ALTER TABLE fantasyscore OWNER TO hallmank;

--
-- Name: fantasyscore_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE fantasyscore_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE fantasyscore_id_seq OWNER TO hallmank;

--
-- Name: fantasyscore_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE fantasyscore_id_seq OWNED BY fantasyscore.id;


--
-- Name: fantasyswim; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE fantasyswim (
    id integer NOT NULL,
    meet_id integer NOT NULL,
    swim_id integer NOT NULL,
    status character varying(255) NOT NULL,
    team_id integer NOT NULL
);


ALTER TABLE fantasyswim OWNER TO hallmank;

--
-- Name: fantasyswim_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE fantasyswim_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE fantasyswim_id_seq OWNER TO hallmank;

--
-- Name: fantasyswim_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE fantasyswim_id_seq OWNED BY fantasyswim.id;


--
-- Name: fantasyteam; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE fantasyteam (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    conference_id integer NOT NULL,
    owner_id integer
);


ALTER TABLE fantasyteam OWNER TO hallmank;

--
-- Name: fantasyteam_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE fantasyteam_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE fantasyteam_id_seq OWNER TO hallmank;

--
-- Name: fantasyteam_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE fantasyteam_id_seq OWNED BY fantasyteam.id;


--
-- Name: fantasyteamswimmer; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE fantasyteamswimmer (
    id integer NOT NULL,
    team_id integer NOT NULL,
    swimmer_id integer NOT NULL,
    conference_id integer NOT NULL
);


ALTER TABLE fantasyteamswimmer OWNER TO hallmank;

--
-- Name: fantasyteamswimmer_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE fantasyteamswimmer_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE fantasyteamswimmer_id_seq OWNER TO hallmank;

--
-- Name: fantasyteamswimmer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE fantasyteamswimmer_id_seq OWNED BY fantasyteamswimmer.id;


--
-- Name: improvement; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE improvement (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    event character varying(255) NOT NULL,
    improvement real NOT NULL,
    fromtime real NOT NULL,
    totime real NOT NULL,
    fromseason integer NOT NULL,
    toseason integer NOT NULL,
    team character varying(255) NOT NULL,
    gender character varying(255) NOT NULL,
    conference character varying(255) NOT NULL,
    division character varying(255) NOT NULL,
    fromyear character varying(255) NOT NULL,
    toyear character varying(255) NOT NULL,
    swimmer_id integer
);


ALTER TABLE improvement OWNER TO hallmank;

--
-- Name: improvement_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE improvement_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE improvement_id_seq OWNER TO hallmank;

--
-- Name: improvement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE improvement_id_seq OWNED BY improvement.id;


--
-- Name: meetstats; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE meetstats (
    id integer NOT NULL,
    percent real NOT NULL,
    place integer NOT NULL,
    conference character varying(255) NOT NULL,
    "numWeeks" integer NOT NULL
);


ALTER TABLE meetstats OWNER TO hallmank;

--
-- Name: meetstats_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE meetstats_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE meetstats_id_seq OWNER TO hallmank;

--
-- Name: meetstats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE meetstats_id_seq OWNED BY meetstats.id;


--
-- Name: swim; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE swim (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    event character varying(255) NOT NULL,
    date date NOT NULL,
    "time" real NOT NULL,
    season integer NOT NULL,
    team character varying(255) NOT NULL,
    meet character varying(255) NOT NULL,
    gender character varying(255) NOT NULL,
    division character varying(255) NOT NULL,
    relay boolean NOT NULL,
    swimmer_id integer,
    powerpoints integer
);


ALTER TABLE swim OWNER TO hallmank;

--
-- Name: swim_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE swim_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE swim_id_seq OWNER TO hallmank;

--
-- Name: swim_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE swim_id_seq OWNED BY swim.id;


--
-- Name: swimmer; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE swimmer (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    season integer NOT NULL,
    gender character varying(255) NOT NULL,
    year character varying(255),
    team_id integer,
    eventppts character varying(255),
    ppts integer
);


ALTER TABLE swimmer OWNER TO hallmank;

--
-- Name: swimmer_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE swimmer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE swimmer_id_seq OWNER TO hallmank;

--
-- Name: swimmer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE swimmer_id_seq OWNED BY swimmer.id;


--
-- Name: swimstaging; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE swimstaging (
    id integer NOT NULL,
    meet character varying(255) NOT NULL,
    date date NOT NULL,
    season integer NOT NULL,
    name character varying(255) NOT NULL,
    year character varying(255),
    team character varying(255) NOT NULL,
    gender character varying(255) NOT NULL,
    event character varying(255) NOT NULL,
    "time" real NOT NULL,
    division character varying(255) NOT NULL,
    relay boolean NOT NULL,
    conference character varying(255),
    new boolean NOT NULL
);


ALTER TABLE swimstaging OWNER TO hallmank;

--
-- Name: swimstaging_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE swimstaging_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE swimstaging_id_seq OWNER TO hallmank;

--
-- Name: swimstaging_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE swimstaging_id_seq OWNED BY swimstaging.id;


--
-- Name: team; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE team (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    improvement real NOT NULL,
    attrition real NOT NULL,
    strengthdual real NOT NULL,
    strengthinvite real NOT NULL,
    conference character varying(255) NOT NULL,
    division character varying(255) NOT NULL,
    gender character varying(255) NOT NULL
);


ALTER TABLE team OWNER TO hallmank;

--
-- Name: team_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE team_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE team_id_seq OWNER TO hallmank;

--
-- Name: team_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE team_id_seq OWNED BY team.id;


--
-- Name: teamseason; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE teamseason (
    id integer NOT NULL,
    season integer NOT NULL,
    team character varying(255) NOT NULL,
    gender character varying(255) NOT NULL,
    conference character varying(255),
    division character varying(255) NOT NULL,
    winconf real,
    winnats real,
    strengthdual real,
    strengthinvite real,
    attrition real,
    improvement real
);


ALTER TABLE teamseason OWNER TO hallmank;

--
-- Name: teamseason_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE teamseason_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE teamseason_id_seq OWNER TO hallmank;

--
-- Name: teamseason_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE teamseason_id_seq OWNED BY teamseason.id;


--
-- Name: teamstats; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE teamstats (
    id integer NOT NULL,
    team_id integer NOT NULL,
    winnats real,
    winconf real,
    date date NOT NULL,
    toptaper real,
    strengthdual real,
    strengthinvite real,
    week integer,
    natsscore integer,
    confscore integer,
    taper boolean NOT NULL,
    mediantaper real
);


ALTER TABLE teamstats OWNER TO hallmank;

--
-- Name: teamstats_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE teamstats_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE teamstats_id_seq OWNER TO hallmank;

--
-- Name: teamstats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE teamstats_id_seq OWNED BY teamstats.id;


--
-- Name: timedist; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE timedist (
    id integer NOT NULL,
    event character varying(255) NOT NULL,
    gender character varying(255) NOT NULL,
    division character varying(255) NOT NULL,
    mu real NOT NULL,
    sigma real NOT NULL,
    skew boolean,
    a real
);


ALTER TABLE timedist OWNER TO hallmank;

--
-- Name: timedist_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE timedist_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE timedist_id_seq OWNER TO hallmank;

--
-- Name: timedist_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE timedist_id_seq OWNED BY timedist.id;


--
-- Name: top_swim; Type: MATERIALIZED VIEW; Schema: public; Owner: hallmank
--

CREATE MATERIALIZED VIEW top_swim AS
 SELECT a.event,
    a."time",
    a.rank,
    a.name,
    a.meet,
    a.team,
    a.year,
    a.swimmer_id,
    a.season,
    a.gender,
    a.division,
    a.conference,
    a.team_id,
    a.date
   FROM ( SELECT swim.name,
            swim."time",
            swim.event,
            swim.meet,
            swim.team,
            sw.year,
            swim.swimmer_id,
            ts.season,
            sw.gender,
            ts.division,
            ts.conference,
            ts.id AS team_id,
            swim.date,
            rank() OVER (PARTITION BY swim.name, swim.event, ts.id ORDER BY swim."time", swim.date) AS rank
           FROM ((swim
             JOIN swimmer sw ON ((swim.swimmer_id = sw.id)))
             JOIN teamseason ts ON ((sw.team_id = ts.id)))) a
  WHERE (a.rank = 1)
  WITH NO DATA;


ALTER TABLE top_swim OWNER TO hallmank;

--
-- Name: worldswim; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE worldswim (
    id integer NOT NULL,
    swimmer_id integer NOT NULL,
    round character varying(255) NOT NULL,
    course character varying(255) NOT NULL,
    distance character varying(255) NOT NULL,
    stroke character varying(255) NOT NULL,
    "time" integer NOT NULL,
    meet character varying(255) NOT NULL,
    date date NOT NULL,
    heat integer,
    lane integer,
    points integer,
    relay boolean NOT NULL,
    reactiontime integer,
    place integer
);


ALTER TABLE worldswim OWNER TO hallmank;

--
-- Name: worldswim_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE worldswim_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE worldswim_id_seq OWNER TO hallmank;

--
-- Name: worldswim_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE worldswim_id_seq OWNED BY worldswim.id;


--
-- Name: worldswimmer; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE worldswimmer (
    id integer NOT NULL,
    team_id integer NOT NULL,
    lastname character varying(255) NOT NULL,
    firstname character varying(255) NOT NULL,
    gender character varying(255) NOT NULL,
    birthdate date NOT NULL
);


ALTER TABLE worldswimmer OWNER TO hallmank;

--
-- Name: worldswimmer_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE worldswimmer_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE worldswimmer_id_seq OWNER TO hallmank;

--
-- Name: worldswimmer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE worldswimmer_id_seq OWNED BY worldswimmer.id;


--
-- Name: worldteam; Type: TABLE; Schema: public; Owner: hallmank
--

CREATE TABLE worldteam (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    shortname character varying(255) NOT NULL,
    code character varying(255) NOT NULL,
    nation character varying(255) NOT NULL,
    type character varying(255) NOT NULL
);


ALTER TABLE worldteam OWNER TO hallmank;

--
-- Name: worldteam_id_seq; Type: SEQUENCE; Schema: public; Owner: hallmank
--

CREATE SEQUENCE worldteam_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE worldteam_id_seq OWNER TO hallmank;

--
-- Name: worldteam_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hallmank
--

ALTER SEQUENCE worldteam_id_seq OWNED BY worldteam.id;


--
-- Name: clubswim id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY clubswim ALTER COLUMN id SET DEFAULT nextval('clubswim_id_seq'::regclass);


--
-- Name: clubswimmer id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY clubswimmer ALTER COLUMN id SET DEFAULT nextval('clubswimmer_id_seq'::regclass);


--
-- Name: clubteam id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY clubteam ALTER COLUMN id SET DEFAULT nextval('clubteam_id_seq'::regclass);


--
-- Name: clubtimedist id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY clubtimedist ALTER COLUMN id SET DEFAULT nextval('clubtimedist_id_seq'::regclass);


--
-- Name: event id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY event ALTER COLUMN id SET DEFAULT nextval('event_id_seq'::regclass);


--
-- Name: fantasyconference id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyconference ALTER COLUMN id SET DEFAULT nextval('fantasyconference_id_seq'::regclass);


--
-- Name: fantasyowner id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyowner ALTER COLUMN id SET DEFAULT nextval('fantasyowner_id_seq'::regclass);


--
-- Name: fantasyscore id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyscore ALTER COLUMN id SET DEFAULT nextval('fantasyscore_id_seq'::regclass);


--
-- Name: fantasyswim id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyswim ALTER COLUMN id SET DEFAULT nextval('fantasyswim_id_seq'::regclass);


--
-- Name: fantasyteam id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyteam ALTER COLUMN id SET DEFAULT nextval('fantasyteam_id_seq'::regclass);


--
-- Name: fantasyteamswimmer id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyteamswimmer ALTER COLUMN id SET DEFAULT nextval('fantasyteamswimmer_id_seq'::regclass);


--
-- Name: improvement id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY improvement ALTER COLUMN id SET DEFAULT nextval('improvement_id_seq'::regclass);


--
-- Name: meetstats id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY meetstats ALTER COLUMN id SET DEFAULT nextval('meetstats_id_seq'::regclass);


--
-- Name: swim id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY swim ALTER COLUMN id SET DEFAULT nextval('swim_id_seq'::regclass);


--
-- Name: swimmer id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY swimmer ALTER COLUMN id SET DEFAULT nextval('swimmer_id_seq'::regclass);


--
-- Name: swimstaging id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY swimstaging ALTER COLUMN id SET DEFAULT nextval('swimstaging_id_seq'::regclass);


--
-- Name: team id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY team ALTER COLUMN id SET DEFAULT nextval('team_id_seq'::regclass);


--
-- Name: teamseason id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY teamseason ALTER COLUMN id SET DEFAULT nextval('teamseason_id_seq'::regclass);


--
-- Name: teamstats id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY teamstats ALTER COLUMN id SET DEFAULT nextval('teamstats_id_seq'::regclass);


--
-- Name: timedist id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY timedist ALTER COLUMN id SET DEFAULT nextval('timedist_id_seq'::regclass);


--
-- Name: worldswim id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY worldswim ALTER COLUMN id SET DEFAULT nextval('worldswim_id_seq'::regclass);


--
-- Name: worldswimmer id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY worldswimmer ALTER COLUMN id SET DEFAULT nextval('worldswimmer_id_seq'::regclass);


--
-- Name: worldteam id; Type: DEFAULT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY worldteam ALTER COLUMN id SET DEFAULT nextval('worldteam_id_seq'::regclass);


--
-- Name: clubswim clubswim_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY clubswim
    ADD CONSTRAINT clubswim_pkey PRIMARY KEY (id);


--
-- Name: clubswimmer clubswimmer_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY clubswimmer
    ADD CONSTRAINT clubswimmer_pkey PRIMARY KEY (id);


--
-- Name: clubteam clubteam_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY clubteam
    ADD CONSTRAINT clubteam_pkey PRIMARY KEY (id);


--
-- Name: clubtimedist clubtimedist_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY clubtimedist
    ADD CONSTRAINT clubtimedist_pkey PRIMARY KEY (id);


--
-- Name: event event_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY event
    ADD CONSTRAINT event_pkey PRIMARY KEY (id);


--
-- Name: fantasyconference fantasyconference_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyconference
    ADD CONSTRAINT fantasyconference_pkey PRIMARY KEY (id);


--
-- Name: fantasyowner fantasyowner_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyowner
    ADD CONSTRAINT fantasyowner_pkey PRIMARY KEY (id);


--
-- Name: fantasyscore fantasyscore_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyscore
    ADD CONSTRAINT fantasyscore_pkey PRIMARY KEY (id);


--
-- Name: fantasyswim fantasyswim_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyswim
    ADD CONSTRAINT fantasyswim_pkey PRIMARY KEY (id);


--
-- Name: fantasyteam fantasyteam_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyteam
    ADD CONSTRAINT fantasyteam_pkey PRIMARY KEY (id);


--
-- Name: fantasyteamswimmer fantasyteamswimmer_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyteamswimmer
    ADD CONSTRAINT fantasyteamswimmer_pkey PRIMARY KEY (id);


--
-- Name: improvement improvement_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY improvement
    ADD CONSTRAINT improvement_pkey PRIMARY KEY (id);


--
-- Name: meetstats meetstats_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY meetstats
    ADD CONSTRAINT meetstats_pkey PRIMARY KEY (id);


--
-- Name: swim name_event_time_date_key; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY swim
    ADD CONSTRAINT name_event_time_date_key UNIQUE (name, event, "time", date);


--
-- Name: swim swim_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY swim
    ADD CONSTRAINT swim_pkey PRIMARY KEY (id);


--
-- Name: swimmer swimmer_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY swimmer
    ADD CONSTRAINT swimmer_pkey PRIMARY KEY (id);


--
-- Name: swimstaging swimstaging_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY swimstaging
    ADD CONSTRAINT swimstaging_pkey PRIMARY KEY (id);


--
-- Name: team team_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY team
    ADD CONSTRAINT team_pkey PRIMARY KEY (id);


--
-- Name: teamseason teamseason_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY teamseason
    ADD CONSTRAINT teamseason_pkey PRIMARY KEY (id);


--
-- Name: teamstats teamstats_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY teamstats
    ADD CONSTRAINT teamstats_pkey PRIMARY KEY (id);


--
-- Name: teamseason test_key; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY teamseason
    ADD CONSTRAINT test_key UNIQUE (season, team, gender, division);


--
-- Name: timedist timedist_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY timedist
    ADD CONSTRAINT timedist_pkey PRIMARY KEY (id);


--
-- Name: clubtimedist unique_dist; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY clubtimedist
    ADD CONSTRAINT unique_dist UNIQUE (age, event, course, gender);


--
-- Name: worldswim worldswim_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY worldswim
    ADD CONSTRAINT worldswim_pkey PRIMARY KEY (id);


--
-- Name: worldswimmer worldswimmer_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY worldswimmer
    ADD CONSTRAINT worldswimmer_pkey PRIMARY KEY (id);


--
-- Name: worldteam worldteam_pkey; Type: CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY worldteam
    ADD CONSTRAINT worldteam_pkey PRIMARY KEY (id);


--
-- Name: clubswim_swimmer_id; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX clubswim_swimmer_id ON clubswim USING btree (swimmer_id);


--
-- Name: clubswim_swimmer_id_team_id_event_date_time_idx; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE UNIQUE INDEX clubswim_swimmer_id_team_id_event_date_time_idx ON clubswim USING btree (swimmer_id, team_id, event, date, "time");


--
-- Name: clubswim_team_id; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX clubswim_team_id ON clubswim USING btree (team_id);


--
-- Name: clubswimmer_team_age_name_gender_idx; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE UNIQUE INDEX clubswimmer_team_age_name_gender_idx ON clubswimmer USING btree (team, age, name, gender);


--
-- Name: clubteam_team_season_gender_idx; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE UNIQUE INDEX clubteam_team_season_gender_idx ON clubteam USING btree (team, season, gender);


--
-- Name: fantasyscore_conference_id; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX fantasyscore_conference_id ON fantasyscore USING btree (conference_id);


--
-- Name: fantasyscore_team_one_id; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX fantasyscore_team_one_id ON fantasyscore USING btree (team_one_id);


--
-- Name: fantasyscore_team_two_id; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX fantasyscore_team_two_id ON fantasyscore USING btree (team_two_id);


--
-- Name: fantasyswim_meet_id; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX fantasyswim_meet_id ON fantasyswim USING btree (meet_id);


--
-- Name: fantasyswim_swim_id; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX fantasyswim_swim_id ON fantasyswim USING btree (swim_id);


--
-- Name: fantasyswim_team_id; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX fantasyswim_team_id ON fantasyswim USING btree (team_id);


--
-- Name: fantasyteam_conference_id; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX fantasyteam_conference_id ON fantasyteam USING btree (conference_id);


--
-- Name: fantasyteamswimmer_conference_id; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX fantasyteamswimmer_conference_id ON fantasyteamswimmer USING btree (conference_id);


--
-- Name: fantasyteamswimmer_swimmer_id; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX fantasyteamswimmer_swimmer_id ON fantasyteamswimmer USING btree (swimmer_id);


--
-- Name: fantasyteamswimmer_team_id; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX fantasyteamswimmer_team_id ON fantasyteamswimmer USING btree (team_id);


--
-- Name: improvement_name_team_event_fromseason_idx; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE UNIQUE INDEX improvement_name_team_event_fromseason_idx ON improvement USING btree (name, team, event, fromseason);


--
-- Name: swim_name_date_event_time_idx; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX swim_name_date_event_time_idx ON swim USING btree (name, date, event, "time");


--
-- Name: swim_swimmer_id_idx; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX swim_swimmer_id_idx ON swim USING btree (swimmer_id);


--
-- Name: swim_team_idx; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX swim_team_idx ON swim USING btree (team);


--
-- Name: swimmer_name_team_id_season_gender_idx; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE UNIQUE INDEX swimmer_name_team_id_season_gender_idx ON swimmer USING btree (name, team_id, season, gender);


--
-- Name: swimmer_teamid_id_idx; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX swimmer_teamid_id_idx ON swimmer USING btree (team_id);


--
-- Name: teamseason_gender_season_conference_team_idx; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX teamseason_gender_season_conference_team_idx ON teamseason USING btree (gender, season, conference, team);


--
-- Name: teamseason_season_team_idx; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX teamseason_season_team_idx ON teamseason USING btree (season, team);


--
-- Name: teamseason_team_season_idx; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX teamseason_team_season_idx ON teamseason USING btree (team, season);


--
-- Name: teamstats_team_id_week_taper_idx; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE UNIQUE INDEX teamstats_team_id_week_taper_idx ON teamstats USING btree (team_id, week, taper);


--
-- Name: teamstats_teamseasonid_id; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX teamstats_teamseasonid_id ON teamstats USING btree (team_id);


--
-- Name: worldswim_swimmer_id; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX worldswim_swimmer_id ON worldswim USING btree (swimmer_id);


--
-- Name: worldswimmer_team_id; Type: INDEX; Schema: public; Owner: hallmank
--

CREATE INDEX worldswimmer_team_id ON worldswimmer USING btree (team_id);


--
-- Name: clubswim clubswim_swimmer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY clubswim
    ADD CONSTRAINT clubswim_swimmer_id_fkey FOREIGN KEY (swimmer_id) REFERENCES clubswimmer(id);


--
-- Name: clubswim clubswim_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY clubswim
    ADD CONSTRAINT clubswim_team_id_fkey FOREIGN KEY (team_id) REFERENCES clubteam(id);


--
-- Name: fantasyscore fantasyscore_conference_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyscore
    ADD CONSTRAINT fantasyscore_conference_id_fkey FOREIGN KEY (conference_id) REFERENCES fantasyconference(id);


--
-- Name: fantasyscore fantasyscore_team_one_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyscore
    ADD CONSTRAINT fantasyscore_team_one_id_fkey FOREIGN KEY (team_one_id) REFERENCES fantasyteam(id);


--
-- Name: fantasyscore fantasyscore_team_two_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyscore
    ADD CONSTRAINT fantasyscore_team_two_id_fkey FOREIGN KEY (team_two_id) REFERENCES fantasyteam(id);


--
-- Name: fantasyswim fantasyswim_meet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyswim
    ADD CONSTRAINT fantasyswim_meet_id_fkey FOREIGN KEY (meet_id) REFERENCES fantasyscore(id);


--
-- Name: fantasyswim fantasyswim_swim_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyswim
    ADD CONSTRAINT fantasyswim_swim_id_fkey FOREIGN KEY (swim_id) REFERENCES swim(id);


--
-- Name: fantasyswim fantasyswim_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyswim
    ADD CONSTRAINT fantasyswim_team_id_fkey FOREIGN KEY (team_id) REFERENCES fantasyteam(id);


--
-- Name: fantasyteam fantasyteam_conference_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyteam
    ADD CONSTRAINT fantasyteam_conference_id_fkey FOREIGN KEY (conference_id) REFERENCES fantasyconference(id);


--
-- Name: fantasyteam fantasyteam_owner_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyteam
    ADD CONSTRAINT fantasyteam_owner_fkey FOREIGN KEY (owner_id) REFERENCES fantasyowner(id);


--
-- Name: fantasyteamswimmer fantasyteamswimmer_conference_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyteamswimmer
    ADD CONSTRAINT fantasyteamswimmer_conference_id_fkey FOREIGN KEY (conference_id) REFERENCES fantasyconference(id);


--
-- Name: fantasyteamswimmer fantasyteamswimmer_swimmer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyteamswimmer
    ADD CONSTRAINT fantasyteamswimmer_swimmer_id_fkey FOREIGN KEY (swimmer_id) REFERENCES swimmer(id);


--
-- Name: fantasyteamswimmer fantasyteamswimmer_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY fantasyteamswimmer
    ADD CONSTRAINT fantasyteamswimmer_team_id_fkey FOREIGN KEY (team_id) REFERENCES fantasyteam(id);


--
-- Name: swim swim_swimmer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY swim
    ADD CONSTRAINT swim_swimmer_id_fkey FOREIGN KEY (swimmer_id) REFERENCES swimmer(id);


--
-- Name: swimmer swimmer_teamid_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY swimmer
    ADD CONSTRAINT swimmer_teamid_id_fkey FOREIGN KEY (team_id) REFERENCES teamseason(id);


--
-- Name: teamstats teamstats_teamseasonid_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY teamstats
    ADD CONSTRAINT teamstats_teamseasonid_id_fkey FOREIGN KEY (team_id) REFERENCES teamseason(id);


--
-- Name: worldswim worldswim_swimmer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY worldswim
    ADD CONSTRAINT worldswim_swimmer_id_fkey FOREIGN KEY (swimmer_id) REFERENCES worldswimmer(id);


--
-- Name: worldswimmer worldswimmer_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: hallmank
--

ALTER TABLE ONLY worldswimmer
    ADD CONSTRAINT worldswimmer_team_id_fkey FOREIGN KEY (team_id) REFERENCES worldteam(id);


--
-- PostgreSQL database dump complete
--

