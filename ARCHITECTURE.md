# djangocms-named-menus — Architecture & Module Documentation

## Overview

`djangocms-named-menus` is a **django CMS** app that allows administrators to create **custom named navigation menus** — similar to WordPress custom menus. Editors can select, order, and nest CMS pages into named menus via a drag-and-drop admin interface, and then render those menus in templates using a custom template tag.

## Key Features

- **Custom Named Menus**: Create multiple menus (e.g., "Header Nav", "Footer Nav", "Sidebar") with arbitrary page selections and nesting
- **Drag-and-Drop Admin**: jQuery-based admin interface for building menu trees
- **Template Tag**: `{% show_named_menu "menu-slug" %}` renders the menu using standard CMS menu templates
- **Site-Aware**: Menus are scoped to individual sites (multi-site support)
- **Auto-slug**: Menu slugs are auto-generated from the name
- **Caching**: Menu node trees are cached per slug+language
- **Draft/Published Mode**: Automatically maps published page IDs to draft IDs in edit mode
- **Signal-Based Cache Invalidation**: Cache clears when menus or page titles change
- **Unavailable Page Cleanup**: Optionally removes pages from menus that are no longer available in the CMS

## Module Breakdown

### `models.py` — Menu Model
- **`CMSNamedMenu`**: The core model. Stores:
  - `name`: Human-readable menu name
  - `slug`: Auto-generated slug (via `django-autoslug`)
  - `pages`: `JSONField` containing the menu tree structure as nested dicts: `[{"id": <page_id>, "children": [...]}, ...]`
  - `site`: ForeignKey to `django.contrib.sites.Site`
  - `unique_together`: `('slug', 'site')`

### `admin.py` — Admin Interface
- **`CMSNamedMenuAdmin`**: Custom admin with:
  - Site-filtered queryset (only shows menus for current site)
  - `changeform_view()` injects available CMS pages as serialized JSON for the drag-and-drop UI
  - `serialize_navigation()` / `get_cleaned_node()`: Recursively converts CMS menu nodes into simple `{id, title, children}` dicts
  - **`clean_menu()`**: Removes menu entries whose page IDs no longer exist
  - **`get_all_available_ids()`**: Flattens available pages to a set of IDs for validation
- **`LazyEncoder`**: JSON encoder that handles Django's lazy translation strings

### `nodes.py` — Menu Node Retrieval
- **`get_nodes()`**: Gets all CMS menu nodes via `menu_pool.get_renderer()`, filtered to only page nodes (not apphooks, etc.)
- **`anonymous_request`**: Decorator that temporarily replaces the authenticated user with `AnonymousUser` to get the public-facing menu
- **`filter_nodes()`**: Filters out hidden nodes and non-page nodes

### `templatetags/named_cms_menu_tags.py` — Template Tags
- **`ShowNamedMenu`** (extends CMS `ShowMenu`): The `{% show_named_menu %}` template tag.
  - Accepts: `menu_name_or_slug`, `from_level`, `to_level`, `extra_inactive`, `extra_active`, `template`, `namespace`, `root_id`
  - Looks up the named menu by slug (or falls back to name)
  - Builds node tree by mapping menu JSON to actual CMS page nodes
  - Handles draft/published mode conversion
  - Applies CMS menu modifiers and level cutting
- **`build_named_menu_nodes()`**: Core function that loads named menu from DB/cache, maps page IDs to CMS nodes, and builds the node tree
- **`create_node()`**: Recursively creates cleaned node copies with proper parent/child relationships
- **`convert_menu_to_draft_mode()`**: Remaps published page IDs to draft page IDs for edit mode

### `cache.py` — Caching Layer
- Key format: `cms_named_menu_{slug}_{language}`
- **`flatten_menu()`**: Recursively flattens nested menu to a flat list
- **`contains_page()`**: Checks if a page ID exists anywhere in a menu tree
- **`delete_by_page_id()`**: Finds all menus containing a given page ID and invalidates their caches

### `signals.py` — Cache Invalidation Signals
- `post_save`/`post_delete` on `CMSNamedMenu` → clear that menu's cache
- `post_save`/`post_delete` on CMS `Title` → clear caches for menus containing that page

### `settings.py` — Configuration
- `CMS_NAMED_MENUS_CACHE_DURATION`: Cache TTL in seconds (default: 3600)
- `CMS_NAMED_MENUS_NAMESPACES`: Allowed menu namespaces (default: `['CMSMenu']`)
- `CMS_NAMED_MENUS_REMOVE_UNAVAILABLE_PAGES`: Auto-remove unavailable pages (default: `True`)

### `apps.py` — App Configuration
- `CMSNamedMenusConfig`: Loads signals on `ready()`

