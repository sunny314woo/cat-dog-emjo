-- Execute only in a dedicated EMJO database, never in another product's schema.
-- Native SQL, no ORM. Business-key uniqueness is (bucket, record_id).
CREATE TABLE IF NOT EXISTS emjo_mutex (
  id TINYINT UNSIGNED NOT NULL PRIMARY KEY
) ENGINE=InnoDB;
INSERT IGNORE INTO emjo_mutex (id) VALUES (1);
CREATE TABLE IF NOT EXISTS emjo_records (
  bucket VARCHAR(40) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  record_id VARCHAR(191) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  payload JSON NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (bucket, record_id)
) ENGINE=InnoDB;
