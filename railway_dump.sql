--
-- PostgreSQL database dump
--

-- Dumped from database version 16.8 (Debian 16.8-1.pgdg120+1)
-- Dumped by pg_dump version 16.9 (Homebrew)

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: answers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.answers (
    id integer NOT NULL,
    question_id integer NOT NULL,
    user_id integer NOT NULL,
    value integer,
    is_skipped integer,
    created_at timestamp without time zone,
    status character varying(16) DEFAULT 'delivered'::character varying NOT NULL
);


ALTER TABLE public.answers OWNER TO postgres;

--
-- Name: answers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.answers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.answers_id_seq OWNER TO postgres;

--
-- Name: answers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.answers_id_seq OWNED BY public.answers.id;


--
-- Name: applied_migrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.applied_migrations (
    name character varying(255) NOT NULL
);


ALTER TABLE public.applied_migrations OWNER TO postgres;

--
-- Name: blocked_users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.blocked_users (
    id integer NOT NULL,
    user_id integer NOT NULL,
    blocked_user_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.blocked_users OWNER TO postgres;

--
-- Name: blocked_users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.blocked_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.blocked_users_id_seq OWNER TO postgres;

--
-- Name: blocked_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.blocked_users_id_seq OWNED BY public.blocked_users.id;


--
-- Name: chat_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages (
    id integer NOT NULL,
    chat_id integer NOT NULL,
    sender_id integer NOT NULL,
    content_type character varying(16) NOT NULL,
    text_content text,
    file_id character varying(255),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    is_read boolean DEFAULT false NOT NULL
);


ALTER TABLE public.chat_messages OWNER TO postgres;

--
-- Name: chat_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chat_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_messages_id_seq OWNER TO postgres;

--
-- Name: chat_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chat_messages_id_seq OWNED BY public.chat_messages.id;


--
-- Name: chats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chats (
    id integer NOT NULL,
    initiator_id integer NOT NULL,
    recipient_id integer NOT NULL,
    status character varying(16) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    ended_at timestamp without time zone,
    group_id integer DEFAULT 0 NOT NULL,
    updated_at timestamp without time zone
);


ALTER TABLE public.chats OWNER TO postgres;

--
-- Name: chats_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chats_id_seq OWNER TO postgres;

--
-- Name: chats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chats_id_seq OWNED BY public.chats.id;


--
-- Name: contact_reveals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contact_reveals (
    id integer NOT NULL,
    chat_id integer NOT NULL,
    user_id integer NOT NULL,
    revealed_at timestamp without time zone DEFAULT now() NOT NULL,
    contact_type character varying(32) NOT NULL,
    contact_value character varying(255) NOT NULL
);


ALTER TABLE public.contact_reveals OWNER TO postgres;

--
-- Name: contact_reveals_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.contact_reveals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.contact_reveals_id_seq OWNER TO postgres;

--
-- Name: contact_reveals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.contact_reveals_id_seq OWNED BY public.contact_reveals.id;


--
-- Name: group_creators; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.group_creators (
    id integer NOT NULL,
    user_id integer,
    created_at timestamp without time zone
);


ALTER TABLE public.group_creators OWNER TO postgres;

--
-- Name: group_creators_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.group_creators_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.group_creators_id_seq OWNER TO postgres;

--
-- Name: group_creators_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.group_creators_id_seq OWNED BY public.group_creators.id;


--
-- Name: group_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.group_members (
    id integer NOT NULL,
    group_id integer,
    user_id integer,
    nickname character varying(64),
    photo_url character varying(255),
    geolocation_lat double precision,
    geolocation_lon double precision,
    city character varying(128),
    role character varying(32),
    joined_at timestamp without time zone,
    balance integer NOT NULL,
    country character varying(128)
);


ALTER TABLE public.group_members OWNER TO postgres;

--
-- Name: group_members_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.group_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.group_members_id_seq OWNER TO postgres;

--
-- Name: group_members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.group_members_id_seq OWNED BY public.group_members.id;


--
-- Name: groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.groups (
    id integer NOT NULL,
    name character varying(128) NOT NULL,
    description text NOT NULL,
    invite_code character varying(5) NOT NULL,
    creator_user_id integer,
    created_at timestamp without time zone
);


ALTER TABLE public.groups OWNER TO postgres;

--
-- Name: groups_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.groups_id_seq OWNER TO postgres;

--
-- Name: groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.groups_id_seq OWNED BY public.groups.id;


--
-- Name: match_statuses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.match_statuses (
    id integer NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL,
    match_user_id integer NOT NULL,
    status character varying(16) NOT NULL,
    created_at timestamp with time zone
);


ALTER TABLE public.match_statuses OWNER TO postgres;

--
-- Name: match_statuses_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.match_statuses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.match_statuses_id_seq OWNER TO postgres;

--
-- Name: match_statuses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.match_statuses_id_seq OWNED BY public.match_statuses.id;


--
-- Name: matches; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.matches (
    id integer NOT NULL,
    user1_id integer NOT NULL,
    user2_id integer NOT NULL,
    group_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    status character varying(16) DEFAULT 'active'::character varying NOT NULL
);


ALTER TABLE public.matches OWNER TO postgres;

--
-- Name: matches_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.matches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.matches_id_seq OWNER TO postgres;

--
-- Name: matches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.matches_id_seq OWNED BY public.matches.id;


--
-- Name: questions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.questions (
    id integer NOT NULL,
    group_id integer NOT NULL,
    author_id integer NOT NULL,
    text text NOT NULL,
    embedding character varying,
    created_at timestamp without time zone,
    is_deleted integer
);


ALTER TABLE public.questions OWNER TO postgres;

--
-- Name: questions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.questions_id_seq OWNER TO postgres;

--
-- Name: questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.questions_id_seq OWNED BY public.questions.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    telegram_user_id bigint NOT NULL,
    created_at timestamp without time zone,
    current_group_id integer,
    username character varying(64),
    is_active boolean DEFAULT true,
    is_admin boolean DEFAULT false,
    points integer DEFAULT 0,
    updated_at timestamp without time zone,
    bio character varying(500),
    telegram_id bigint,
    language character varying(8)
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: answers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.answers ALTER COLUMN id SET DEFAULT nextval('public.answers_id_seq'::regclass);


--
-- Name: blocked_users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blocked_users ALTER COLUMN id SET DEFAULT nextval('public.blocked_users_id_seq'::regclass);


--
-- Name: chat_messages id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages ALTER COLUMN id SET DEFAULT nextval('public.chat_messages_id_seq'::regclass);


--
-- Name: chats id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chats ALTER COLUMN id SET DEFAULT nextval('public.chats_id_seq'::regclass);


--
-- Name: contact_reveals id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contact_reveals ALTER COLUMN id SET DEFAULT nextval('public.contact_reveals_id_seq'::regclass);


--
-- Name: group_creators id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_creators ALTER COLUMN id SET DEFAULT nextval('public.group_creators_id_seq'::regclass);


--
-- Name: group_members id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_members ALTER COLUMN id SET DEFAULT nextval('public.group_members_id_seq'::regclass);


--
-- Name: groups id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.groups ALTER COLUMN id SET DEFAULT nextval('public.groups_id_seq'::regclass);


--
-- Name: match_statuses id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.match_statuses ALTER COLUMN id SET DEFAULT nextval('public.match_statuses_id_seq'::regclass);


--
-- Name: matches id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matches ALTER COLUMN id SET DEFAULT nextval('public.matches_id_seq'::regclass);


--
-- Name: questions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions ALTER COLUMN id SET DEFAULT nextval('public.questions_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
abcdef123456
\.


--
-- Data for Name: answers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.answers (id, question_id, user_id, value, is_skipped, created_at, status) FROM stdin;
55	20	1	2	\N	2025-05-23 13:07:02.695764	answered
56	20	5	2	\N	2025-05-23 13:07:02.892686	answered
57	16	5	1	\N	2025-05-23 13:07:16.266859	answered
58	17	5	1	\N	2025-05-23 13:07:28.543965	answered
59	18	5	-1	\N	2025-05-23 13:07:35.350095	answered
62	21	5	2	\N	2025-05-23 13:07:49.183117	answered
60	19	5	1	\N	2025-05-23 13:07:39.098146	answered
63	22	1	2	\N	2025-05-23 13:11:42.112332	answered
64	22	5	2	\N	2025-05-23 13:11:42.373681	answered
65	23	1	-1	\N	2025-05-23 13:17:27.568925	answered
66	23	5	-1	\N	2025-05-23 13:17:27.768831	answered
68	24	5	1	\N	2025-05-23 13:26:52.404037	answered
67	24	1	2	\N	2025-05-23 13:26:52.130205	answered
61	21	1	2	\N	2025-05-23 13:07:48.985696	answered
17	8	1	0	0	2025-05-19 13:53:48.983215	answered
71	26	1	0	\N	2025-05-24 11:52:28.855241	answered
70	25	5	2	\N	2025-05-24 11:51:36.464847	answered
72	26	5	-1	\N	2025-05-24 11:52:29.111809	answered
36	7	4	0	1	2025-05-22 21:53:07.769566	delivered
2	2	1	2	0	2025-05-19 09:49:20.273001	answered
3	3	1	1	0	2025-05-19 09:50:24.683888	answered
4	4	1	-2	0	2025-05-19 09:50:39.765799	answered
5	5	1	-1	0	2025-05-19 09:51:44.397119	answered
6	2	2	2	0	2025-05-19 10:51:55.725753	answered
7	3	2	2	0	2025-05-19 10:51:59.46263	answered
8	4	2	0	1	2025-05-19 10:52:02.972099	answered
9	5	2	0	1	2025-05-19 10:52:06.798371	answered
10	2	3	2	0	2025-05-19 11:36:57.745229	answered
11	3	3	2	0	2025-05-19 11:37:00.568312	answered
12	4	3	1	0	2025-05-19 11:37:03.18126	answered
13	5	3	-1	0	2025-05-19 11:37:10.490724	answered
14	6	3	2	0	2025-05-19 11:37:55.966101	answered
45	14	4	0	\N	2025-05-23 11:30:23.68641	delivered
18	9	1	2	0	2025-05-19 15:03:35.379369	answered
40	11	4	1	0	2025-05-22 21:53:29.566383	delivered
20	11	2	2	0	2025-05-20 07:44:14.334512	answered
21	6	2	1	0	2025-05-20 07:44:17.477495	answered
22	7	2	1	0	2025-05-20 07:44:21.766497	answered
23	8	2	1	0	2025-05-20 07:44:24.282788	answered
24	9	2	2	0	2025-05-20 07:44:27.120383	answered
25	10	2	1	0	2025-05-20 07:44:30.414631	answered
27	11	1	2	0	2025-05-20 08:00:25.589129	answered
28	13	1	2	0	2025-05-20 08:26:49.135684	answered
29	13	2	2	0	2025-05-20 10:53:29.456664	answered
30	12	2	2	0	2025-05-20 10:53:32.357292	answered
31	2	4	2	0	2025-05-22 21:51:30.612038	answered
32	3	4	1	0	2025-05-22 21:51:37.373485	answered
33	4	4	-2	0	2025-05-22 21:52:47.603057	answered
34	5	4	-1	0	2025-05-22 21:52:52.562741	answered
35	6	4	1	0	2025-05-22 21:52:57.528739	answered
37	8	4	-2	0	2025-05-22 21:53:15.029807	answered
38	9	4	2	0	2025-05-22 21:53:17.985243	answered
39	10	4	1	0	2025-05-22 21:53:22.354096	answered
75	27	3	\N	\N	2025-05-25 11:54:56.441026	delivered
41	12	4	-1	0	2025-05-22 21:53:34.651733	answered
42	13	4	1	0	2025-05-22 21:53:38.679527	answered
46	14	3	\N	\N	2025-05-23 11:30:23.939151	delivered
43	14	1	2	\N	2025-05-23 11:30:23.024071	answered
16	6	1	1	0	2025-05-19 13:34:05.169102	answered
50	15	3	\N	\N	2025-05-23 11:46:58.838659	delivered
47	15	1	-1	\N	2025-05-23 11:46:58.181851	answered
44	14	2	2	\N	2025-05-23 11:30:23.440836	answered
48	15	2	-1	\N	2025-05-23 11:46:58.395359	answered
49	15	4	2	\N	2025-05-23 11:46:58.624265	answered
51	16	1	2	\N	2025-05-23 13:01:25.679721	answered
52	17	1	-1	\N	2025-05-23 13:03:45.848012	answered
53	18	1	1	\N	2025-05-23 13:05:16.989924	answered
54	19	1	1	\N	2025-05-23 13:05:57.881704	answered
69	25	1	2	\N	2025-05-24 11:51:36.177317	delivered
19	10	1	2	0	2025-05-19 17:25:01.485495	delivered
26	12	1	2	0	2025-05-20 08:00:19.966691	answered
73	27	1	-1	\N	2025-05-25 11:54:55.869399	answered
76	27	2	-1	\N	2025-05-25 11:54:56.692278	answered
74	27	4	-1	\N	2025-05-25 11:54:56.158994	answered
15	7	1	1	0	2025-05-19 13:33:58.795929	answered
\.


--
-- Data for Name: applied_migrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.applied_migrations (name) FROM stdin;
2024_10_add_group_id_to_chats.py
m2024_01_create_matches_table.py
m2024_02_add_group_id_to_matches.py
m2024_06_add_groupmember_nickname_photo.py
m2024_07_add_match_group_id.py
m2024_07_chatbot_core_tables.py
m2024_08_add_telegram_id_to_users.py
m2024_08_create_chats_table.py
m2024_09_add_telegram_id_to_users.py
m2024_09_add_username_to_users.py
m2024_11_add_is_active_to_users.py
m2024_12_add_is_admin_to_users.py
m2024_13_add_points_to_users.py
m2024_14_add_updated_at_to_users.py
m2024_15_add_bio_to_users.py
run_all.py
m2024_03_add_updated_at_to_chats.py
\.


--
-- Data for Name: blocked_users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.blocked_users (id, user_id, blocked_user_id, created_at) FROM stdin;
\.


--
-- Data for Name: chat_messages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chat_messages (id, chat_id, sender_id, content_type, text_content, file_id, created_at, is_read) FROM stdin;
1	2	1	text	хеллоу	\N	2025-05-20 17:41:24.305648	t
3	2	1	text	а можно ли обменяться контактами?	\N	2025-05-20 18:02:12.457195	f
2	2	2	text	привет привет	\N	2025-05-20 17:41:40.111304	t
4	2	2	text	картинками пока нет	\N	2025-05-20 18:02:38.633908	t
5	2	2	text	I'd like to connect directly.\n\nMy nickname: TestAccount\nMy Telegram: @tier2botadmin	\N	2025-05-20 18:02:48.196815	t
6	3	5	text	Сработало	\N	2025-05-23 14:14:07.365895	f
7	3	5	text	А сейчас?	\N	2025-05-23 14:52:51.142499	f
8	3	5	text	Выглядит прочтённым сразу	\N	2025-05-23 14:53:09.351214	f
\.


--
-- Data for Name: chats; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chats (id, initiator_id, recipient_id, status, created_at, ended_at, group_id, updated_at) FROM stdin;
2	1	2	active	2025-05-20 15:42:48.711041	\N	1	2025-05-20 15:42:48.711043
3	1	5	active	2025-05-23 13:55:32.395965	\N	2	2025-05-23 13:55:32.395968
4	4	3	active	2025-05-23 15:42:30.420433	\N	1	2025-05-23 15:42:30.420435
\.


--
-- Data for Name: contact_reveals; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.contact_reveals (id, chat_id, user_id, revealed_at, contact_type, contact_value) FROM stdin;
\.


--
-- Data for Name: group_creators; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.group_creators (id, user_id, created_at) FROM stdin;
1	1	2025-05-18 15:17:09.063991
\.


--
-- Data for Name: group_members; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.group_members (id, group_id, user_id, nickname, photo_url, geolocation_lat, geolocation_lon, city, role, joined_at, balance, country) FROM stdin;
6	2	1	Dima	AgACAgIAAxkBAAIJ_WgwcTLNdhEEflz6g_J-Ef8iq2EBAAIz-DEb42aBSW2Ve-KVMKHYAQADAgADeQADNgQ	55.753519	37.670622	\N	member	2025-05-23 12:59:13.626589	524	\N
7	2	5	Rmq	AgACAgIAAxkBAAIKUmgwemIwkOsgMI9-qqEPrgcF32GcAALr7DEbGNuJScYSYFx6mlrQAQADAgADeQADNgQ	53.958649	27.658464	\N	member	2025-05-23 13:06:43.159437	31	\N
2	1	2	TestAccount	AgACAgIAAxkBAAII82grDT766JH2gy7M1shufn52HdIRAALh7TEbrVxYSTCsyIdtuPGuAQADAgADbQADNgQ	\N	\N	Moscow	member	2025-05-19 10:41:54.309573	5	Russia
4	1	4	Artem	AgACAgIAAxkBAAIJjmgvnFTWZp6vijLrp-OgvVCsMY_oAAJG-jEbZSx4SQfGuBdi-YPJAQADAgADeQADNgQ	55.71679	37.608559	\N	member	2025-05-22 21:50:36.03435	26	\N
1	1	1	Dima	AgACAgIAAxkBAAIInWgp_I3uVW8xQ5tJe42-nmn_TDJQAAKz9DEbvERRSSunAAEymZUKpgEAAwIAA3kAAzYE	55.753113	37.670905	\N	member	2025-05-18 15:27:23.094239	529	\N
3	1	3	Alex	AgACAgIAAxkBAAIJBWgrF8Rt8l6oE1OuziLwR1ZPqt2DAAJv8jEbhnxYST5KgpUK6UYSAQADAgADeQADNgQ	\N	\N	Amsterdam	member	2025-05-19 11:35:57.657484	75	Netherlands
5	\N	1	\N	\N	\N	\N	\N	member	2025-05-23 12:59:01.77	0	\N
\.


--
-- Data for Name: groups; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.groups (id, name, description, invite_code, creator_user_id, created_at) FROM stdin;
1	Allkinds Dev Team	Mostly for testing purposes, but still let's try to be conscice here	TO68Q	1	2025-05-18 15:27:23.090692
2	Veloceraptor	Музыка, философия, строительство и не только (тестируем)	H16W1	1	2025-05-23 12:59:01.766997
\.


--
-- Data for Name: match_statuses; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.match_statuses (id, user_id, group_id, match_user_id, status, created_at) FROM stdin;
1	1	1	2	matched	2025-05-20 13:13:47.289567+00
2	2	1	1	matched	2025-05-20 13:13:47.295333+00
4	5	2	1	matched	2025-05-23 13:19:43.40858+00
5	1	2	5	matched	2025-05-23 14:51:01.901261+00
6	4	1	3	matched	2025-05-23 15:42:19.084514+00
7	3	1	4	matched	2025-05-23 15:42:19.088286+00
\.


--
-- Data for Name: matches; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.matches (id, user1_id, user2_id, group_id, created_at, status) FROM stdin;
1	1	2	1	2025-05-20 13:13:47.300823+00	active
2	1	5	2	2025-05-23 13:19:43.410691+00	active
3	3	4	1	2025-05-23 15:42:19.090897+00	active
\.


--
-- Data for Name: questions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.questions (id, group_id, author_id, text, embedding, created_at, is_deleted) FROM stdin;
1	1	1	Могу задавать вопросы?	\N	2025-05-18 15:46:16.541389	1
2	1	1	Ты был бы готов встретиться с человеком отсюда вживую?	\N	2025-05-19 09:49:16.593925	0
3	1	1	Ты интересуешься психологией?	\N	2025-05-19 09:50:22.127188	0
4	1	1	Гедонизм наше все?	\N	2025-05-19 09:50:36.090818	0
5	1	1	Ты берешь в магазине самые "красивые" фрукты?	\N	2025-05-19 09:51:41.723635	0
6	1	3	Используешь велосипед как вид транспорта?	\N	2025-05-19 11:37:43.226385	0
7	1	1	Все эти разговоры про где лучше жить, где вкуснее еда и пр - суета?	\N	2025-05-19 13:33:44.981596	0
8	1	1	Do you believe real strength is in vulnerability?	\N	2025-05-19 13:53:30.623111	0
9	1	1	Тебе важно докопаться до сути?	\N	2025-05-19 15:03:27.51522	0
10	1	1	Ты играешь в шахматы хотя бы раз в неделю?	\N	2025-05-19 17:24:52.750799	0
11	1	2	Вода это лучший напиток?	\N	2025-05-20 07:44:05.962076	0
12	1	1	Ты читал книги Нила Стивенсона?	\N	2025-05-20 07:53:12.191621	0
13	1	1	У тебя есть мысль, что ты можешь/должен прожить "выдающуюся" жизнь?	\N	2025-05-20 08:26:44.418722	0
14	1	1	Если ты уронишь телефон в унитаз - достанешь его сразу же голыми руками? 🙃	\N	2025-05-23 11:30:21.133782	0
15	1	1	У тебя есть любимые поры года?	\N	2025-05-23 11:46:56.26008	0
16	2	1	Немного инфы.. \n- Вопросы - от всех нас\n- свои вопросы можно удалять\n- можно переответить на любой вопрос..\n\nПонятно?	\N	2025-05-23 13:01:23.810977	0
17	2	1	Жалеешь о чем-то в прошлом?	\N	2025-05-23 13:03:43.835817	0
18	2	1	Слушали новый альбом Виагра Бойс?	\N	2025-05-23 13:05:14.946989	0
19	2	1	Хм. А если в тусовке и так все с большего все друг о друге знают - это все имеет смысл?	\N	2025-05-23 13:05:55.98844	0
20	2	1	Тебе нормально 2 часа потратить на то, чтобы играть, искать, оттачивать один трек?	\N	2025-05-23 13:07:00.692727	0
21	2	1	Творчество это необходимость для тебя?	\N	2025-05-23 13:07:47.253087	0
22	2	1	Кстати, чтобы задать вопрос - просто набери его и отошли как сообщение. Ферштеен?	\N	2025-05-23 13:11:40.125332	0
23	2	1	У тебя сейчас скорее белая полоса? 🦓	\N	2025-05-23 13:17:25.48689	0
24	2	1	Нужно ли выстраивать свои границы?	\N	2025-05-23 13:26:50.147385	0
25	2	1	А готов был бы на месяц на 2 репетиции в неделю подписаться?	\N	2025-05-24 11:51:34.22562	0
26	2	1	Ты сейчас скорее плывешь по течению?	\N	2025-05-24 11:52:26.928645	0
27	1	1	Вы могли бы жить с человеком, который во всем с вами соглашается (вроде комфортно), но при этом не думает особо своей головой?	\N	2025-05-25 11:54:53.929564	0
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, telegram_user_id, created_at, current_group_id, username, is_active, is_admin, points, updated_at, bio, telegram_id, language) FROM stdin;
2	7994646552	2025-05-19 10:41:19.906529	1	\N	t	f	0	\N	\N	\N	\N
3	1698974271	2025-05-19 11:34:25.667386	1	\N	t	f	0	\N	\N	\N	\N
4	233737364	2025-05-22 21:50:00.987158	1	\N	t	f	0	\N	\N	\N	\N
5	285154302	2025-05-23 13:06:43.140231	2	\N	t	f	0	\N	\N	\N	en
1	179382367	2025-05-18 15:01:57.661481	1	\N	t	f	0	\N	\N	\N	\N
\.


--
-- Name: answers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.answers_id_seq', 76, true);


--
-- Name: blocked_users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.blocked_users_id_seq', 1, false);


--
-- Name: chat_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.chat_messages_id_seq', 8, true);


--
-- Name: chats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.chats_id_seq', 4, true);


--
-- Name: contact_reveals_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.contact_reveals_id_seq', 1, false);


--
-- Name: group_creators_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.group_creators_id_seq', 1, true);


--
-- Name: group_members_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.group_members_id_seq', 7, true);


--
-- Name: groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.groups_id_seq', 2, true);


--
-- Name: match_statuses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.match_statuses_id_seq', 7, true);


--
-- Name: matches_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.matches_id_seq', 3, true);


--
-- Name: questions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.questions_id_seq', 27, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 5, true);


--
-- Name: group_members _group_user_uc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT _group_user_uc UNIQUE (group_id, user_id);


--
-- Name: matches _match_pair_uc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT _match_pair_uc UNIQUE (user1_id, user2_id, group_id);


--
-- Name: match_statuses _match_uc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.match_statuses
    ADD CONSTRAINT _match_uc UNIQUE (user_id, group_id, match_user_id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: answers answers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.answers
    ADD CONSTRAINT answers_pkey PRIMARY KEY (id);


--
-- Name: applied_migrations applied_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.applied_migrations
    ADD CONSTRAINT applied_migrations_pkey PRIMARY KEY (name);


--
-- Name: blocked_users blocked_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blocked_users
    ADD CONSTRAINT blocked_users_pkey PRIMARY KEY (id);


--
-- Name: blocked_users blocked_users_user_id_blocked_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blocked_users
    ADD CONSTRAINT blocked_users_user_id_blocked_user_id_key UNIQUE (user_id, blocked_user_id);


--
-- Name: chat_messages chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (id);


--
-- Name: chats chats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chats
    ADD CONSTRAINT chats_pkey PRIMARY KEY (id);


--
-- Name: contact_reveals contact_reveals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contact_reveals
    ADD CONSTRAINT contact_reveals_pkey PRIMARY KEY (id);


--
-- Name: group_creators group_creators_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_creators
    ADD CONSTRAINT group_creators_pkey PRIMARY KEY (id);


--
-- Name: group_creators group_creators_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_creators
    ADD CONSTRAINT group_creators_user_id_key UNIQUE (user_id);


--
-- Name: group_members group_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_pkey PRIMARY KEY (id);


--
-- Name: groups groups_invite_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_invite_code_key UNIQUE (invite_code);


--
-- Name: groups groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_pkey PRIMARY KEY (id);


--
-- Name: match_statuses match_statuses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.match_statuses
    ADD CONSTRAINT match_statuses_pkey PRIMARY KEY (id);


--
-- Name: matches matches_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_pkey PRIMARY KEY (id);


--
-- Name: questions questions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_telegram_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_telegram_id_key UNIQUE (telegram_id);


--
-- Name: users users_telegram_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_telegram_user_id_key UNIQUE (telegram_user_id);


--
-- Name: idx_chat_messages_chat_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_messages_chat_id ON public.chat_messages USING btree (chat_id);


--
-- Name: idx_chat_messages_is_read; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_messages_is_read ON public.chat_messages USING btree (is_read);


--
-- Name: idx_chat_messages_sender_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_messages_sender_id ON public.chat_messages USING btree (sender_id);


--
-- Name: ix_answers_user_id_question_id_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_answers_user_id_question_id_status ON public.answers USING btree (user_id, question_id, status);


--
-- Name: answers answers_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.answers
    ADD CONSTRAINT answers_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.questions(id) ON DELETE CASCADE;


--
-- Name: answers answers_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.answers
    ADD CONSTRAINT answers_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: blocked_users blocked_users_blocked_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blocked_users
    ADD CONSTRAINT blocked_users_blocked_user_id_fkey FOREIGN KEY (blocked_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: blocked_users blocked_users_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blocked_users
    ADD CONSTRAINT blocked_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: chat_messages chat_messages_chat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES public.chats(id) ON DELETE CASCADE;


--
-- Name: chat_messages chat_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: chats chats_initiator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chats
    ADD CONSTRAINT chats_initiator_id_fkey FOREIGN KEY (initiator_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: chats chats_recipient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chats
    ADD CONSTRAINT chats_recipient_id_fkey FOREIGN KEY (recipient_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: contact_reveals contact_reveals_chat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contact_reveals
    ADD CONSTRAINT contact_reveals_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES public.chats(id) ON DELETE CASCADE;


--
-- Name: contact_reveals contact_reveals_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contact_reveals
    ADD CONSTRAINT contact_reveals_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: group_creators group_creators_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_creators
    ADD CONSTRAINT group_creators_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: group_members group_members_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: group_members group_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: groups groups_creator_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_creator_user_id_fkey FOREIGN KEY (creator_user_id) REFERENCES public.users(id);


--
-- Name: match_statuses match_statuses_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.match_statuses
    ADD CONSTRAINT match_statuses_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: match_statuses match_statuses_match_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.match_statuses
    ADD CONSTRAINT match_statuses_match_user_id_fkey FOREIGN KEY (match_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: match_statuses match_statuses_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.match_statuses
    ADD CONSTRAINT match_statuses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: matches matches_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: matches matches_user1_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_user1_id_fkey FOREIGN KEY (user1_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: matches matches_user2_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_user2_id_fkey FOREIGN KEY (user2_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: questions questions_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: questions questions_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: users users_current_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_current_group_id_fkey FOREIGN KEY (current_group_id) REFERENCES public.groups(id);


--
-- PostgreSQL database dump complete
--

