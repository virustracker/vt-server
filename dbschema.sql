CREATE TYPE report_type AS ENUM ('SELF_REPORT', 'VERIFIED');
CREATE TYPE report_result AS ENUM ('UNKNOWN', 'POSITIVE', 'NEGATIVE');

CREATE TABLE token (token_value bytea PRIMARY KEY, report_type report_type NOT NULL, report_result report_result NOT NULL);
COMMENT ON TABLE token is 'Contains one row per uploaded token. If a token is submitted in multiple reports, its row reflects the latest report.';
COMMENT ON COLUMN token.token_value is 'The token value as transmitted via Bluetooth. Always 32 bytes.';

CREATE TABLE certificate (attestation_hash_prefix bytea PRIMARY KEY, result report_result NOT NULL, lab_id bigint NOT NULL);
COMMENT ON TABLE certificate is 'Submitted attestation certificates.';
COMMENT ON COLUMN certificate.attestation_hash_prefix is 'The hash prefix as given to lab personnel. At least 8 bytes.';
COMMENT ON COLUMN certificate.lab_id is '(always positive)';

CREATE TABLE lab (id bigint PRIMARY KEY, key bytea NOT NULL);
COMMENT ON TABLE lab is 'Registered labs and their HMAC keys.';
COMMENT ON COLUMN lab.id is '(always positive)';
COMMENT ON COLUMN lab.key is 'The HMAC key this lab uses in its attestations.';
