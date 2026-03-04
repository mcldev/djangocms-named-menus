import json

from django.utils.functional import Promise
from django.utils.encoding import force_str

from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.contrib import admin

from cms_named_menus.models import CMSNamedMenu
from cms_named_menus.nodes import get_nodes
from cms_named_menus.settings import ALLOWED_NAMESPACES, REMOVE_UNAVAILABLE_PAGES
from cms_named_menus.cache import flatten_menu


class LazyEncoder(json.JSONEncoder):
    """Encodes django's lazy i18n strings.
        Used to serialize translated strings to JSON, because
        simplejson chokes on it otherwise. """

    def default(self, obj):
        if isinstance(obj, Promise):
            return force_str(obj)
        return obj


class SimpleNode(object):
    id = None
    title = None
    children = []

    def __init__(self, node):
        self.id = node.id
        self.title = node.title


def get_all_available_ids(nodes):
    ret = []
    for node in nodes:
        node_id = getattr(node, 'id', node.get('id'))
        ret.append(node_id)
        children = node.get('children', [])
        if children:
            ret.extend(get_all_available_ids(children))
    return ret


def clean_menu(menu, available_ids):
    removed_nodes = []
    for node in reversed(menu):
        if node.get('id') not in available_ids:
            menu.remove(node)
            removed_nodes.append(node)
        else:
            children = node.get('children', [])
            if children:
                removed_nodes.extend(clean_menu(children, available_ids))

    return removed_nodes


class CMSNamedMenuAdmin(admin.ModelAdmin):
    change_form_template = 'cms_named_menus/change_form.html'
    readonly_fields = ('site',)
    list_display = ('name', 'slug', 'site')
    save_on_top = True

    def get_queryset(self, request):
        qs = super(CMSNamedMenuAdmin, self).get_queryset(request)
        current_site = get_current_site(request)
        return qs.filter(site=current_site)

    def changeform_view(self, request, object_id = None, form_url = '', extra_context = None):
        nodes, menu_renderer = get_nodes(request)
        available_pages = self.serialize_navigation(nodes)
        # Get defaults - i.e. for a new menu
        removed_nodes = []
        menu_pages = CMSNamedMenu.objects.none()
        # If change form, get the menu pages and remove unavailable pages
        if object_id:
            menu_pages = CMSNamedMenu.objects.get(id=object_id).pages
            # Need to take all menu_pages and map to available pages, or REMOVE them!
            # then, on save the menu is updated without removed pages...
            if REMOVE_UNAVAILABLE_PAGES:
                available_ids = get_all_available_ids(available_pages)
                removed_nodes = clean_menu(menu_pages, available_ids)

        extra_context = {
            'menu_pages': menu_pages,
            'removed_nodes': removed_nodes,
            'available_pages': available_pages,
            'available_pages_json': json.dumps(available_pages, cls=LazyEncoder),
            'debug': settings.DEBUG,
        }
        return super(CMSNamedMenuAdmin, self).changeform_view(request, object_id, form_url, extra_context)

    def serialize_navigation(self, all_nodes):
        # Recursively convert nodes to simple nodes
        cleaned = []
        for node in all_nodes:
            if not node.parent_id:
                cleaned_node = self.get_cleaned_node([node])
                if cleaned_node:
                    cleaned += cleaned_node

        return cleaned

    def get_cleaned_node(self, nodes):
        # Clean node to be a simple title/id/children class
        cleaned_nodes = []
        for node in nodes:
            # Limit the namespaces, typically to CMS Page only, can be set to None to ignore this
            if ALLOWED_NAMESPACES and node.namespace not in ALLOWED_NAMESPACES:
                continue
            cleaned_node = SimpleNode(node)
            if node.children:
                child_nodes = self.get_cleaned_node(node.children)
                if child_nodes:
                    cleaned_node.children = child_nodes
            cleaned_nodes.append(cleaned_node.__dict__)

        return cleaned_nodes


admin.site.register(CMSNamedMenu, CMSNamedMenuAdmin)
