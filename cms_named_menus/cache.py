# -*- coding: utf-8 -*-
'''
Created on May 21, 2016

@author: jakob
'''

from django.conf import settings
from django.core.cache import cache

from cms_named_menus.models import CMSNamedMenu
from cms_named_menus.settings import CACHE_DURATION


def flatten_menu(menu):
    ret = []
    for node in menu:
        ret.append(node)
        children = node.get('children', [])
        if children:
            ret.extend(flatten_menu(children))
    return ret


def contains_page(menu, page_id):
    flat_menu = flatten_menu(menu)
    for node in flat_menu:
        if node['id'] == page_id:
            return True


def _key(menu_slug, language=""):
    return 'cms_named_menu_{slug}_{lang}'.format(lang=language, slug=menu_slug)


def get(menu_slug, language=""):
    key = _key(menu_slug, language)
    return cache.get(key, None)


def set(menu_slug, nodes, language=""):  # @ReservedAssignment
    key = _key(menu_slug, language)
    cache.set(key, nodes, CACHE_DURATION)


def delete(menu_slug, language=""):
    delete_many([menu_slug], language)


def delete_many(menu_slugs, language=""):
    for menu_slug in menu_slugs:
        key = _key(menu_slug, language)
        cache.delete(key)


def delete_by_page_id(page_id=None):
    menu_slugs = []
    for menu in CMSNamedMenu.objects.all():
        if menu.pages and contains_page(menu.pages, page_id):
            menu_slugs.append(menu.slug)

    delete_many(menu_slugs)
