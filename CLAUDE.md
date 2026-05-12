# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`djangocms-named-menus` is a **distributable django CMS app** (installed as `cms_named_menus`) that adds WordPress-style custom named menus to django CMS. It is *not* a Django project — there is no `manage.py`. The `tests/` directory contains a minimal Django settings module used to drive `django-admin test`.

Pinned dependencies (see `setup.py`):
- `Django>=4.2,<5.0`
- `django-cms>=3.11,<3.12`
- `django-classy-tags`, `django-autoslug>=1.7.2`

## Common commands

Run from the repo root.

```bash
# Install package + test deps in editable mode
pip install -e ".[test]"

# Full test suite (uses tests/settings.py + in-memory SQLite)
python -m django test tests --settings=tests.settings

# Verbose
python -m django test tests --settings=tests.settings -v 2

# Single test class / method
python -m django test tests.test_named_menus.CMSNamedMenuModelTests --settings=tests.settings
python -m django test tests.test_named_menus.CMSNamedMenuModelTests.test_str --settings=tests.settings
```

`test_filter_by_json_content` auto-skips on SQLite (needs PostgreSQL or MariaDB ≥ 10.2.3 for JSON `contains`).

There is no separate lint/format step configured.

## Architecture

The package is small but the data flow has a few non-obvious moving parts. The **same menu** is represented in three different shapes that you have to translate between:

1. **Stored JSON** in `CMSNamedMenu.pages` — nested `[{"id": <page_id>, "children": [...]}]`. Only IDs, no titles.
2. **Available CMS pages** — full CMS menu nodes pulled from `menu_pool` (used by the admin UI to populate the right-hand panel).
3. **Rendered tree** — CMS `NavigationNode` objects produced at template-tag time by hydrating the stored IDs against the live menu pool.

Modules and their roles:

- **`models.py`** — `CMSNamedMenu(name, slug, pages: JSONField, site)` with `unique_together=(slug, site)` and `django-autoslug` slugifying `name`.
- **`admin.py`** — `CMSNamedMenuAdmin` filters the changelist queryset to the current site, and `changeform_view()` injects available CMS pages as JSON for the drag/drop UI. `clean_menu()` recursively prunes entries whose page IDs no longer exist (gated by `CMS_NAMED_MENUS_REMOVE_UNAVAILABLE_PAGES`). `LazyEncoder` handles Django lazy translation strings during JSON serialization.
- **`nodes.py`** — `get_nodes()` calls `menu_pool.get_renderer(...)` filtered to namespaces in `ALLOWED_NAMESPACES`. The `anonymous_request` decorator swaps in `AnonymousUser` so the admin UI sees the public-facing tree (not draft-only nodes).
- **`templatetags/named_cms_menu_tags.py`** — `{% show_named_menu %}` extends CMS `ShowMenu`. `build_named_menu_nodes()` loads the named menu (via cache → DB), then `create_node()` recursively maps stored IDs to deep-copied CMS nodes. `convert_menu_to_draft_mode()` remaps published page IDs → draft IDs in edit mode (this is the seam between published & draft views — change with care).
- **`cache.py`** — Cache key format: `cms_named_menu_{slug}_{language}`. `delete_by_page_id()` iterates **all** `CMSNamedMenu` rows and uses `contains_page()` to find which to invalidate (deliberately avoids JSON `contains` lookups for SQLite/MySQL portability — see commit `b905252`).
- **`signals.py`** — `post_save`/`post_delete` on `CMSNamedMenu` invalidates that menu's cache; the same signals on CMS `Title` fan out via `delete_by_page_id()` so menus containing a renamed/deleted page get cleared.
- **`settings.py`** — Reads `CMS_NAMED_MENUS_CACHE_DURATION` (3600), `CMS_NAMED_MENUS_NAMESPACES` (`['CMSMenu']`, set to `None` to allow all), `CMS_NAMED_MENUS_REMOVE_UNAVAILABLE_PAGES` (True).
- **`apps.py`** — `CMSNamedMenusConfig.ready()` imports signals.

### Admin drag-and-drop UI

The admin builder under `static/cmsnamedmenus/` was modernized from jQuery Nestable to **vanilla JS + SortableJS** (see `UPGRADE_GUIDE.md`, `MODERNIZATION_SUMMARY.md`). Key pieces:

- `static/cmsnamedmenus/js/menu-builder.js` — `MenuBuilder` class; `serializeMenu()` writes the nested JSON back into a hidden form field on every change. Exposed as `window.menuBuilder`.
- `static/cmsnamedmenus/js/sortable.min.js` — SortableJS library.
- `static/cmsnamedmenus/css/menu-builder.css` — CSS Grid/Flexbox layout.
- `templates/cms_named_menus/admin_select.html` — wires the builder into the admin change form. `menu_item.html` is the per-item template.

The current branch (`upgrade/js-2026`) is iterating on this UI; recent commits (`b905252`, `880c58a`) touched cache invalidation and admin CSS/template positioning. The "old" jQuery template/files referenced in `UPGRADE_GUIDE.md` may already be gone — verify before relying on rollback paths described there.

### Migrations

Migrations live in `cms_named_menus/migrations/`. The notable one is `0009_alter_pages_to_django_jsonfield.py` — `pages` is a real Django `JSONField` (not a text field of JSON), so on PostgreSQL/MariaDB you can use JSON lookups; SQLite/MySQL paths in the codebase intentionally avoid them.