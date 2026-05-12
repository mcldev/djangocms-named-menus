from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.sites.models import Site
from autoslug.fields import AutoSlugField
from django.conf import settings


def get_current_site():
    try:
        current_site = Site.objects.get_current()
        if current_site:
            return current_site.id
    except:
        return settings.SITE_ID
    else:
        return settings.SITE_ID


class CMSNamedMenu(models.Model):
    name = models.CharField(max_length=255)
    slug = AutoSlugField(always_update=False,
                         populate_from='name',
                         unique=True)
    pages = models.JSONField(blank=True,
                             null=True,
                             default=list)

    site = models.ForeignKey(Site,
                             on_delete=models.CASCADE,
                             help_text=_('The site the menu is accessible at.'),
                             verbose_name=_("site"),
                             default=get_current_site)

    def __str__(self):
        return self.name


    class Meta:
        verbose_name = "CMS Menu"
        verbose_name_plural = "CMS Menus"
        unique_together = ('slug', 'site',)
