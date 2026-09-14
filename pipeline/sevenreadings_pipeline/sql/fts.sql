-- Full-text indexes, built by the pipeline after all rows are loaded.
-- External-content tables: no duplicated text, rebuilt in one pass.
CREATE VIRTUAL TABLE commentary_fts USING fts5(
  heading, body, source_id UNINDEXED,
  content='commentary_entries', content_rowid='id',
  tokenize='unicode61 remove_diacritics 2'
);
INSERT INTO commentary_fts(commentary_fts) VALUES ('rebuild');

CREATE VIRTUAL TABLE verses_fts USING fts5(
  body, translation_id UNINDEXED,
  content='verses', content_rowid='id',
  tokenize='unicode61 remove_diacritics 2'
);
INSERT INTO verses_fts(verses_fts) VALUES ('rebuild');
