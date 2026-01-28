--
-- PostgreSQL database dump
--

\restrict PjGP99jyqWBoM3vlEmrDc6VOqkgguyEhv2eJW0DeC6AfTyCcxskAezklzFYdrHw

-- Dumped from database version 15.15
-- Dumped by pg_dump version 15.15

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
-- Name: data_temp; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.data_temp (
    id integer NOT NULL,
    sensor character varying(100) NOT NULL,
    temperature double precision NOT NULL,
    humidity double precision NOT NULL,
    date_serveur timestamp without time zone DEFAULT '2026-01-28 12:39:35.968083'::timestamp without time zone,
    average_temperature double precision,
    average_humidity double precision,
    fan_status boolean,
    humidifier_status boolean,
    numfailedsensors integer
);


ALTER TABLE public.data_temp OWNER TO "user";

--
-- Name: data_temp_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.data_temp_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.data_temp_id_seq OWNER TO "user";

--
-- Name: data_temp_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.data_temp_id_seq OWNED BY public.data_temp.id;


--
-- Name: login; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.login (
    id integer NOT NULL,
    mail_id character varying(255),
    user_name character varying(100) NOT NULL,
    password character varying(255) NOT NULL,
    status boolean,
    created_at timestamp without time zone DEFAULT '2026-01-28 12:39:35.968083'::timestamp without time zone
);


ALTER TABLE public.login OWNER TO "user";

--
-- Name: login_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.login_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.login_id_seq OWNER TO "user";

--
-- Name: login_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.login_id_seq OWNED BY public.login.id;


--
-- Name: parameter_data; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.parameter_data (
    id integer NOT NULL,
    temperature double precision NOT NULL,
    humidity double precision NOT NULL,
    start_date timestamp without time zone NOT NULL,
    stat_stepper boolean,
    number_stepper integer,
    espece character varying(50) NOT NULL,
    timetoclose integer,
    created_at timestamp without time zone DEFAULT '2026-01-28 12:39:35.968083'::timestamp without time zone
);


ALTER TABLE public.parameter_data OWNER TO "user";

--
-- Name: parameter_data_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.parameter_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.parameter_data_id_seq OWNER TO "user";

--
-- Name: parameter_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.parameter_data_id_seq OWNED BY public.parameter_data.id;


--
-- Name: stepper; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.stepper (
    id integer NOT NULL,
    start_date time without time zone,
    status boolean,
    created_at timestamp without time zone DEFAULT '2026-01-28 12:39:35.968083'::timestamp without time zone
);


ALTER TABLE public.stepper OWNER TO "user";

--
-- Name: stepper_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.stepper_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stepper_id_seq OWNER TO "user";

--
-- Name: stepper_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.stepper_id_seq OWNED BY public.stepper.id;


--
-- Name: data_temp id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.data_temp ALTER COLUMN id SET DEFAULT nextval('public.data_temp_id_seq'::regclass);


--
-- Name: login id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.login ALTER COLUMN id SET DEFAULT nextval('public.login_id_seq'::regclass);


--
-- Name: parameter_data id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.parameter_data ALTER COLUMN id SET DEFAULT nextval('public.parameter_data_id_seq'::regclass);


--
-- Name: stepper id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.stepper ALTER COLUMN id SET DEFAULT nextval('public.stepper_id_seq'::regclass);


--
-- Data for Name: data_temp; Type: TABLE DATA; Schema: public; Owner: user
--

COPY public.data_temp (id, sensor, temperature, humidity, date_serveur, average_temperature, average_humidity, fan_status, humidifier_status, numfailedsensors) FROM stdin;
1	sensor_01	22.5	55	2026-01-28 12:39:35.968083	22.5	55	t	f	0
2	sensor_02	23	58	2026-01-28 12:39:35.968083	23	58	t	f	0
3	sensor_03	21.8	52.5	2026-01-28 12:39:35.968083	21.8	52.5	f	t	0
\.


--
-- Data for Name: login; Type: TABLE DATA; Schema: public; Owner: user
--

COPY public.login (id, mail_id, user_name, password, status, created_at) FROM stdin;
1	admin@smartelia.local	admin	$2b$12$1o6AivzrWUHg2gLpMyQtqudLlfWow18z1P7UZV/JJUzSu9wAI94tm	t	2026-01-28 12:39:35.968083
\.


--
-- Data for Name: parameter_data; Type: TABLE DATA; Schema: public; Owner: user
--

COPY public.parameter_data (id, temperature, humidity, start_date, stat_stepper, number_stepper, espece, timetoclose, created_at) FROM stdin;
\.


--
-- Data for Name: stepper; Type: TABLE DATA; Schema: public; Owner: user
--

COPY public.stepper (id, start_date, status, created_at) FROM stdin;
\.


--
-- Name: data_temp_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.data_temp_id_seq', 3, true);


--
-- Name: login_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.login_id_seq', 2, true);


--
-- Name: parameter_data_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.parameter_data_id_seq', 1, false);


--
-- Name: stepper_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.stepper_id_seq', 1, false);


--
-- Name: data_temp data_temp_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.data_temp
    ADD CONSTRAINT data_temp_pkey PRIMARY KEY (id);


--
-- Name: login login_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.login
    ADD CONSTRAINT login_pkey PRIMARY KEY (id);


--
-- Name: login login_user_name_key; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.login
    ADD CONSTRAINT login_user_name_key UNIQUE (user_name);


--
-- Name: parameter_data parameter_data_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.parameter_data
    ADD CONSTRAINT parameter_data_pkey PRIMARY KEY (id);


--
-- Name: stepper stepper_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.stepper
    ADD CONSTRAINT stepper_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict PjGP99jyqWBoM3vlEmrDc6VOqkgguyEhv2eJW0DeC6AfTyCcxskAezklzFYdrHw

