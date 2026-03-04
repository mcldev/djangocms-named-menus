"""
Unit tests for djangocms-named-menus.
Verifies models, cache utilities, admin helpers, template tag helpers, and signals
work correctly with Django 4.2, djangoCMS 3.11, and Python 3.11.
"""
import json

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase, RequestFactory, override_settings

from cms.api import create_page
from cms.test_utils.testcases import CMSTestCase

from cms_named_menus.models import CMSNamedMenu, get_current_site
from cms_named_menus.cache import (
    flatten_menu, contains_page, _key as cache_key,
)
from cms_named_menus import cache as menu_cache
from cms_named_menus.admin import (
    get_all_available_ids, clean_menu, SimpleNode, LazyEncoder,
)
from cms_named_menus.settings import CACHE_DURATION, ALLOWED_NAMESPACES


# ============================================================
# Model Tests
# ============================================================

class CMSNamedMenuModelTests(TestCase):
    """Test CMSNamedMenu model."""

    def setUp(self):
        self.site = Site.objects.get_current()

    def test_create_menu(self):
        menu = CMSNamedMenu.objects.create(
            name='Main Navigation',
            site=self.site,
            pages=[],
        )
        self.assertEqual(menu.name, 'Main Navigation')
        self.assertIsNotNone(menu.slug)
        self.assertEqual(menu.site, self.site)

    def test_str_returns_name(self):
        menu = CMSNamedMenu.objects.create(
            name='Footer Menu',
            site=self.site,
            pages=[],
        )
        self.assertEqual(str(menu), 'Footer Menu')

    def test_auto_slug_generated(self):
        menu = CMSNamedMenu.objects.create(
            name='My Test Menu',
            site=self.site,
            pages=[],
        )
        self.assertEqual(menu.slug, 'my-test-menu')

    def test_pages_default_is_empty_list(self):
        menu = CMSNamedMenu.objects.create(
            name='Empty',
            site=self.site,
        )
        self.assertEqual(menu.pages, [])

    def test_pages_stores_nested_json(self):
        pages = [
            {'id': 1, 'children': [{'id': 2, 'children': []}]},
            {'id': 3, 'children': []},
        ]
        menu = CMSNamedMenu.objects.create(
            name='Nested',
            site=self.site,
            pages=pages,
        )
        menu.refresh_from_db()
        self.assertEqual(len(menu.pages), 2)
        self.assertEqual(menu.pages[0]['id'], 1)
        self.assertEqual(menu.pages[0]['children'][0]['id'], 2)

    def test_unique_together_slug_site(self):
        CMSNamedMenu.objects.create(name='Unique', site=self.site, pages=[])
        with self.assertRaises(Exception):
            CMSNamedMenu.objects.create(name='Unique', site=self.site, pages=[])

    def test_meta_verbose_names(self):
        self.assertEqual(CMSNamedMenu._meta.verbose_name, 'CMS Menu')
        self.assertEqual(CMSNamedMenu._meta.verbose_name_plural, 'CMS Menus')


class GetCurrentSiteTests(TestCase):
    """Test the get_current_site() helper function."""

    def test_returns_site_id(self):
        site_id = get_current_site()
        self.assertIsNotNone(site_id)
        self.assertEqual(site_id, Site.objects.get_current().id)


# ============================================================
# Cache Utility Tests
# ============================================================

class FlattenMenuTests(TestCase):
    """Test the flatten_menu() function."""

    def test_flat_menu(self):
        menu = [
            {'id': 1, 'children': []},
            {'id': 2, 'children': []},
        ]
        flat = flatten_menu(menu)
        self.assertEqual(len(flat), 2)
        ids = [n['id'] for n in flat]
        self.assertIn(1, ids)
        self.assertIn(2, ids)

    def test_nested_menu(self):
        menu = [
            {'id': 1, 'children': [
                {'id': 2, 'children': []},
                {'id': 3, 'children': [
                    {'id': 4, 'children': []}
                ]},
            ]},
        ]
        flat = flatten_menu(menu)
        self.assertEqual(len(flat), 4)
        ids = [n['id'] for n in flat]
        self.assertEqual(ids, [1, 2, 3, 4])

    def test_empty_menu(self):
        self.assertEqual(flatten_menu([]), [])


class ContainsPageTests(TestCase):
    """Test the contains_page() function."""

    def test_page_found_at_top(self):
        menu = [{'id': 5, 'children': []}]
        self.assertTrue(contains_page(menu, 5))

    def test_page_found_nested(self):
        menu = [{'id': 1, 'children': [{'id': 2, 'children': []}]}]
        self.assertTrue(contains_page(menu, 2))

    def test_page_not_found(self):
        menu = [{'id': 1, 'children': []}]
        self.assertIsNone(contains_page(menu, 99))


class CacheKeyTests(TestCase):
    """Test cache key format."""

    def test_key_format(self):
        key = cache_key('main-nav', 'en')
        self.assertEqual(key, 'cms_named_menu_main-nav_en')

    def test_key_no_language(self):
        key = cache_key('footer')
        self.assertEqual(key, 'cms_named_menu_footer_')


class CacheSetGetDeleteTests(TestCase):
    """Test cache set/get/delete operations."""

    def test_set_and_get(self):
        nodes = [{'id': 1, 'title': 'Home'}]
        menu_cache.set('test-menu', nodes, 'en')
        result = menu_cache.get('test-menu', 'en')
        self.assertEqual(result, nodes)

    def test_get_returns_none_for_missing(self):
        result = menu_cache.get('nonexistent', 'en')
        self.assertIsNone(result)

    def test_delete(self):
        menu_cache.set('del-test', [{'id': 1}], 'en')
        menu_cache.delete('del-test', 'en')
        self.assertIsNone(menu_cache.get('del-test', 'en'))

    def test_delete_many(self):
        menu_cache.set('slug1', [{'id': 1}], 'en')
        menu_cache.set('slug2', [{'id': 2}], 'en')
        menu_cache.delete_many(['slug1', 'slug2'], 'en')
        self.assertIsNone(menu_cache.get('slug1', 'en'))
        self.assertIsNone(menu_cache.get('slug2', 'en'))


# ============================================================
# Admin Helper Tests
# ============================================================

class GetAllAvailableIdsTests(TestCase):
    """Test the get_all_available_ids() admin helper."""

    def test_flat_list(self):
        nodes = [
            {'id': 1, 'children': []},
            {'id': 2, 'children': []},
        ]
        ids = get_all_available_ids(nodes)
        self.assertEqual(ids, [1, 2])

    def test_nested_list(self):
        nodes = [
            {'id': 1, 'children': [
                {'id': 2, 'children': [
                    {'id': 3, 'children': []}
                ]},
            ]},
        ]
        ids = get_all_available_ids(nodes)
        self.assertEqual(ids, [1, 2, 3])

    def test_empty_list(self):
        self.assertEqual(get_all_available_ids([]), [])


class CleanMenuTests(TestCase):
    """Test the clean_menu() admin helper."""

    def test_removes_unavailable(self):
        menu = [
            {'id': 1, 'children': []},
            {'id': 2, 'children': []},
            {'id': 3, 'children': []},
        ]
        available_ids = [1, 3]
        removed = clean_menu(menu, available_ids)
        self.assertEqual(len(menu), 2)
        remaining_ids = [n['id'] for n in menu]
        self.assertIn(1, remaining_ids)
        self.assertIn(3, remaining_ids)
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0]['id'], 2)

    def test_removes_unavailable_children(self):
        menu = [
            {'id': 1, 'children': [
                {'id': 2, 'children': []},
                {'id': 3, 'children': []},
            ]},
        ]
        available_ids = [1, 2]
        removed = clean_menu(menu, available_ids)
        self.assertEqual(len(menu), 1)
        self.assertEqual(len(menu[0]['children']), 1)
        self.assertEqual(menu[0]['children'][0]['id'], 2)
        self.assertEqual(len(removed), 1)

    def test_all_available(self):
        menu = [
            {'id': 1, 'children': []},
            {'id': 2, 'children': []},
        ]
        removed = clean_menu(menu, [1, 2])
        self.assertEqual(len(menu), 2)
        self.assertEqual(len(removed), 0)

    def test_empty_menu(self):
        menu = []
        removed = clean_menu(menu, [])
        self.assertEqual(len(menu), 0)
        self.assertEqual(len(removed), 0)


class SimpleNodeTests(TestCase):
    """Test the SimpleNode helper class."""

    def test_creates_from_node(self):
        class MockNode:
            id = 42
            title = 'Home Page'
        node = SimpleNode(MockNode())
        self.assertEqual(node.id, 42)
        self.assertEqual(node.title, 'Home Page')


class LazyEncoderTests(TestCase):
    """Test LazyEncoder handles Django lazy strings."""

    def test_encodes_lazy_string(self):
        from django.utils.translation import gettext_lazy as _
        lazy_str = _('Hello World')
        result = json.dumps({'title': lazy_str}, cls=LazyEncoder)
        parsed = json.loads(result)
        self.assertEqual(parsed['title'], 'Hello World')

    def test_encodes_normal_types(self):
        data = {'key': 'value', 'num': 42, 'flag': True}
        result = json.dumps(data, cls=LazyEncoder)
        parsed = json.loads(result)
        self.assertEqual(parsed, data)


# ============================================================
# Settings Tests
# ============================================================

class SettingsTests(TestCase):
    """Test default settings values."""

    def test_cache_duration_default(self):
        self.assertEqual(CACHE_DURATION, 3600)

    def test_allowed_namespaces_default(self):
        self.assertEqual(ALLOWED_NAMESPACES, ['CMSMenu'])


# ============================================================
# Signal Tests
# ============================================================

class SignalTests(TestCase):
    """Test that signals are connected and fire correctly."""

    def setUp(self):
        self.site = Site.objects.get_current()

    def test_cache_cleared_on_menu_save(self):
        # Pre-populate cache
        menu_cache.set('signal-test', [{'id': 1}], '')
        self.assertIsNotNone(menu_cache.get('signal-test', ''))

        # Create a menu with that slug — signal should clear the cache
        menu = CMSNamedMenu.objects.create(
            name='signal-test',
            site=self.site,
            pages=[{'id': 1, 'children': []}],
        )
        # The post_save signal should have called cache.delete(instance.slug)
        self.assertIsNone(menu_cache.get('signal-test', ''))

    def test_cache_cleared_on_menu_delete(self):
        menu = CMSNamedMenu.objects.create(
            name='delete-test',
            site=self.site,
            pages=[],
        )
        menu_cache.set('delete-test', [{'id': 1}], '')
        menu.delete()
        self.assertIsNone(menu_cache.get('delete-test', ''))


# ============================================================
# Admin Integration Tests
# ============================================================

class CMSNamedMenuAdminTests(CMSTestCase):
    """Test admin views work correctly."""

    def setUp(self):
        self.site = Site.objects.get_current()
        self.superuser = User.objects.create_superuser(
            username='admin', password='admin', email='admin@test.com')

    def test_admin_changelist_accessible(self):
        self.client.login(username='admin', password='admin')
        response = self.client.get('/admin/cms_named_menus/cmsnamedmenu/')
        self.assertEqual(response.status_code, 200)

    def test_admin_add_form_accessible(self):
        self.client.login(username='admin', password='admin')
        response = self.client.get('/admin/cms_named_menus/cmsnamedmenu/add/')
        self.assertEqual(response.status_code, 200)

    def test_admin_change_form_accessible(self):
        menu = CMSNamedMenu.objects.create(
            name='Admin Test', site=self.site, pages=[])
        self.client.login(username='admin', password='admin')
        response = self.client.get(f'/admin/cms_named_menus/cmsnamedmenu/{menu.id}/change/')
        self.assertEqual(response.status_code, 200)

    def test_admin_shows_site_filtered_menus(self):
        """Admin should only show menus for the current site."""
        other_site = Site.objects.create(domain='other.com', name='Other')
        CMSNamedMenu.objects.create(name='This Site', site=self.site, pages=[])
        CMSNamedMenu.objects.create(name='Other Site', site=other_site, pages=[])

        self.client.login(username='admin', password='admin')
        response = self.client.get('/admin/cms_named_menus/cmsnamedmenu/')
        self.assertContains(response, 'This Site')
        self.assertNotContains(response, 'Other Site')


# ============================================================
# JSONField Migration Tests
# ============================================================

class JSONFieldTests(TestCase):
    """Verify JSONField works correctly after migration from jsonfield to Django JSONField."""

    def setUp(self):
        self.site = Site.objects.get_current()

    def test_store_and_retrieve_list(self):
        menu = CMSNamedMenu.objects.create(
            name='JSON Test',
            site=self.site,
            pages=[{'id': 1, 'children': [{'id': 2, 'children': []}]}],
        )
        menu.refresh_from_db()
        self.assertIsInstance(menu.pages, list)
        self.assertEqual(menu.pages[0]['id'], 1)

    def test_store_empty_list(self):
        menu = CMSNamedMenu.objects.create(
            name='Empty JSON', site=self.site, pages=[])
        menu.refresh_from_db()
        self.assertEqual(menu.pages, [])

    def test_store_null(self):
        menu = CMSNamedMenu.objects.create(
            name='Null JSON', site=self.site, pages=None)
        menu.refresh_from_db()
        self.assertIsNone(menu.pages)

    def test_filter_by_json_content(self):
        """Verify that Django's native JSONField supports contains lookups."""
        CMSNamedMenu.objects.create(
            name='Searchable', site=self.site,
            pages=[{'id': 42, 'children': []}])
        # This uses Django's JSONField lookup capabilities
        qs = CMSNamedMenu.objects.filter(pages__contains=[{'id': 42, 'children': []}])
        self.assertTrue(qs.exists())

