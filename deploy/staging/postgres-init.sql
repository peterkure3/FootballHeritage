-- This file runs only on a newly initialized, isolated staging volume.
\getenv api_password STAGING_API_PASSWORD
\getenv pipeline_password STAGING_PIPELINE_PASSWORD
\getenv readonly_password STAGING_READONLY_PASSWORD
CREATE ROLE fh_api LOGIN PASSWORD :'api_password';
CREATE ROLE fh_pipeline LOGIN PASSWORD :'pipeline_password';
CREATE ROLE fh_readonly LOGIN PASSWORD :'readonly_password';
CREATE DATABASE fh_staging_app;
CREATE DATABASE fh_staging_predictions;
CREATE DATABASE fh_staging_tests;
\connect fh_staging_app
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO fh_api;
ALTER DEFAULT PRIVILEGES FOR ROLE staging_owner IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO fh_api;
ALTER DEFAULT PRIVILEGES FOR ROLE staging_owner IN SCHEMA public GRANT USAGE,SELECT ON SEQUENCES TO fh_api;
\connect fh_staging_predictions
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE,CREATE ON SCHEMA public TO fh_pipeline;
GRANT USAGE ON SCHEMA public TO fh_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE staging_owner IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO fh_pipeline;
ALTER DEFAULT PRIVILEGES FOR ROLE staging_owner IN SCHEMA public GRANT USAGE,SELECT ON SEQUENCES TO fh_pipeline;
ALTER DEFAULT PRIVILEGES FOR ROLE staging_owner IN SCHEMA public GRANT SELECT ON TABLES TO fh_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE fh_pipeline IN SCHEMA public GRANT SELECT ON TABLES TO fh_readonly;
