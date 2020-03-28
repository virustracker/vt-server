CREATE TYPE report_type AS ENUM ('SELF_REPORT', 'VERIFIED');
CREATE TYPE report_result AS ENUM ('UNKNOWN', 'POSITIVE', 'NEGATIVE');

CREATE TABLE token (token bytea PRIMARY KEY, location_lat double precision NULL, location_long double precision NULL, report_type report_type NOT NULL, report_result report_result NOT NULL);

COMMENT ON TABLE token is 'Contains one row per uploaded token. If a token is submitted in multiple reports, its row reflects the latest report.';
COMMENT ON COLUMN token.token is 'The token as transmitted via Bluetooth. Always 16 bytes.';
