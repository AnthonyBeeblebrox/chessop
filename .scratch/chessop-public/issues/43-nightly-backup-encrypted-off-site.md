# 43: Nightly backup, encrypted off-site

**What to build:** `chessop maintain` ends by taking a backup of the database through SQLite's backup API (never a file copy) into the data directory's backups folder, keeping 14, then encrypting it with `age` to the configured recipient and uploading it to the configured bucket with the write-only key. With the `CHESSOP_BACKUP_*` variables unset the upload is skipped and logged. The step follows `maintain`'s rules: idempotent, counts logged, failure gives a non-zero exit. (Spec §13, §14.)

**Blocked by:** 42

**Status:** done

- [x] After `maintain`, a restorable backup of the live database exists in the backups folder
- [x] Only the 14 most recent local backups are kept
- [x] With the backup variables set, the uploaded object is `age`-encrypted and decrypts with the matching key (upload asserted against a stub)
- [x] With them unset, the upload is skipped with a log line and the run still exits zero
- [x] A failed upload exits non-zero and leaves the local backup in place
