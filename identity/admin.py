from django.contrib import admin
from django.utils.safestring import mark_safe

from sorl.thumbnail.admin import AdminImageMixin

from identity.models import Identity
from uploads.models import Entity


class EntityIdentityInlineAdmin(AdminImageMixin, admin.TabularInline):
    model = Identity.identity.through
    extra = 0
    max_num = 0

    readonly_fields = ["get_image"]

    def get_image(self, obj):
        obj = obj.entity
        if obj.has_image():
            return mark_safe('<img src="%s">' % obj.image.url)
        return "No crop yet"


class EntityMatchInlineAdmin(AdminImageMixin, admin.TabularInline):
    model = Identity.matchs.through
    extra = 0
    max_num = 0

    readonly_fields = ["get_image"]

    def get_image(self, obj):
        obj = obj.entity
        if obj.has_image():
            return mark_safe('<img src="%s">' % obj.image.url)
        return "No crop yet"


class IdentityAdmin(AdminImageMixin, admin.ModelAdmin):
    inlines = [
        EntityIdentityInlineAdmin,
        EntityMatchInlineAdmin,
    ]


admin.site.register(Identity, IdentityAdmin)
