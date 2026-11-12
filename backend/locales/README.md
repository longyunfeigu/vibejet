Place compiled translation files under this folder.

Structure:

locales/
  en/LC_MESSAGES/messages.po|mo
  zh_Hans/LC_MESSAGES/messages.po|mo

Edit the .po files by hand: code looks messages up by key (`t("key")` / `message_key=`),
which `pybabel extract` cannot see, so extract + update would mark every entry obsolete.

- Validate: uv run python scripts/validate_po.py (syntax + key coverage; also a pre-commit hook)
- Compile:  uv run pybabel compile -d locales
