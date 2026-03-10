import logging
from copy import deepcopy

from autoslug.utils import slugify
from classytags.arguments import IntegerArgument, Argument, StringArgument
from classytags.core import Options
from cms.models import Page, menu_pool
from cms.utils.moderator import use_draft
from django import template
from django.core.exceptions import ObjectDoesNotExist
from menus.templatetags.menu_tags import ShowMenu, flatten, cut_levels

from cms_named_menus import cache
from cms_named_menus.models import CMSNamedMenu
from cms_named_menus.nodes import filter_nodes

logger = logging.getLogger(__name__)

register = template.Library()


def clean_node(node, level, namespace):

    # Remove nodes not in this namespace
    if namespace and not node.namespace == namespace:
        return None

    new_node = deepcopy(node)
    new_node.parent = None
    new_node.children = []
    new_node.level = level
    # Return Deepcopy which allows duplicated nodes throughout
    return new_node


# Create a cleaned copy of node, called recursively with children
def create_node(item, page_nodes, level=0, namespace=None):

    # Id and Child menu items defined in named menu
    page_id = item['id']
    child_items = item.get('children', [])

    # Return none if the page_id in the json is no longer in the node page ids
    if page_id not in page_nodes:
        return None

    # Get Page node cleaned
    page_node = page_nodes[page_id]

    page_node = clean_node(page_node, level, namespace)

    if page_node is None:
        return None

    # If child items, call recursively to add child nodes
    if child_items:
        level += 1
        for child_item in child_items:
            child_node = create_node(child_item, page_nodes, level=level, namespace=namespace)
            if child_node:
                child_node.parent = page_node
                page_node.children.append(child_node)

    return page_node


def convert_menu_to_draft_mode(menu):
    # Flatten nodes and get all page ids
    nodes = cache.flatten_menu(menu)
    published_page_ids = [a['id'] for a in nodes]

    # Load all published pages with node relationship (prevent N+1)
    published_pages = Page.objects.filter(id__in=published_page_ids).select_related('node')

    # Create a map from published id > draft id for draft mode
    page_map = {}
    for page in published_pages:
        page_map[page.id] = page.publisher_public_id

    # modify all menu nodes in-situ > return None id if page deleted
    for node in nodes:
        node['id'] = page_map.get(node['id'], None)


# Build the named menu
def build_named_menu_nodes(menu_name_or_slug, page_nodes, draft_mode_active, language, namespace=None):

    # Return if no nodes!
    if not page_nodes:
        return

    # Get the name and derive the slug - for the cache key
    menu_slug = slugify(menu_name_or_slug)

    logger.debug(u'Creating Named Menu: "{}"'.format(menu_slug))

    # Get named menu from cache if available, no caching in edit mode!~
    # --------------------------------
    named_menu = None
    if not draft_mode_active:
        named_menu = cache.get(menu_slug, language)
        if named_menu:
            return named_menu

    # Rebuild named menu if not cached and not in draft mode - post-cut/levels/etc happens after
    # --------------------------------
    # Get by Slug or from Menu name - backwards compatible
    try:
        named_menu = CMSNamedMenu.objects.get(slug__exact=menu_slug).pages
    except ObjectDoesNotExist:
        try:
            named_menu = CMSNamedMenu.objects.get(name__iexact=menu_name_or_slug).pages
        except ObjectDoesNotExist:
            logger.info(u'Named menu with name(slug): "%s" not found', menu_name_or_slug)

    # If we get the named menu, build the nodes
    if named_menu:
        named_menu_nodes = []

        # Convert to draft mode if required
        if draft_mode_active:
            convert_menu_to_draft_mode(named_menu)

        for item in named_menu:
            # Loops through each [{'id':[page_id], 'children':[,,]},... etc
            # Maps nodes and child nodes
            node = create_node(item, page_nodes, level=0, namespace=namespace)
            if node is not None:
                named_menu_nodes.append(node)

        # Cache named menu to avoid repeated queries
        if not draft_mode_active:
            cache.set(menu_slug, named_menu_nodes, language)

        return named_menu_nodes


class ShowNamedMenu(ShowMenu):

    name = 'show_named_menu'

    options = Options(
        StringArgument('menu_name_or_slug', required=True),
        IntegerArgument('from_level', default=0, required=False),
        IntegerArgument('to_level', default=100, required=False),
        IntegerArgument('extra_inactive', default=0, required=False),
        IntegerArgument('extra_active', default=1000, required=False),
        StringArgument('template', default='menu/menu.html', required=False),
        StringArgument('namespace', default=None, required=False),
        StringArgument('root_id', default=None, required=False),
        Argument('next_page', default=None, required=False),
    )

    def get_context(self, context, menu_name_or_slug, from_level, to_level, extra_inactive,
                    extra_active, template, namespace, root_id, next_page):

        # From menus.template_tags.menu_tags.py
        try:
            # If there's an exception (500), default context_processors may not be called.
            request = context['request']
        except KeyError:
            return {'template': 'menu/empty.html'}

        if next_page:
            children = next_page.children
        else:

            # new menu... get all the data so we can save a lot of queries
            menu_renderer = context.get('cms_menu_renderer')

            if not menu_renderer:
                menu_renderer = menu_pool.get_renderer(request)

            # Get Nodes hopefully from cached page nodes above in context
            nodes = menu_renderer.get_nodes(namespace, root_id)
            nodes = filter_nodes(nodes)

            # Ceate a page_node dictionary
            page_nodes = {n.id: n for n in nodes}

            # Get if in Draft or Published mode
            draft_mode_active = use_draft(request)

            # Get Language to ensure separate cache of page nodes
            language = getattr(request, 'LANGUAGE_CODE', "")

            # Build or get from cache - Named menu nodes
            nodes = build_named_menu_nodes(menu_name_or_slug, page_nodes, draft_mode_active, language, namespace=namespace)

            # If nodes returned, then cut levels and apply modifiers
            if nodes:
                # Post-Cut ... apply cut levels and menu modifiers
                nodes = flatten(nodes)
                children = cut_levels(nodes, from_level, to_level, extra_inactive, extra_active)
                children = menu_renderer.apply_modifiers(children, namespace, root_id, post_cut=True)
            else:
                children = []

        # Return the context, or go straight to template which will present missing etc.
        try:
            context['children'] = children
            context['template'] = template
            context['from_level'] = from_level
            context['to_level'] = to_level
            context['extra_inactive'] = extra_inactive
            context['extra_active'] = extra_active
            context['namespace'] = namespace
        except:
            context = {"template": template}

        return context


register.tag(ShowNamedMenu)
