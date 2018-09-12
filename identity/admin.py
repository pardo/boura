from django.contrib import admin, messages
from django.utils.safestring import mark_safe

from sorl.thumbnail.admin import AdminImageMixin

from identity.models import Identity, IdentityMatch
from uploads.models import Entity
from inline_actions.admin import InlineActionsModelAdminMixin, InlineActionsMixin


class EntityIdentityInlineAdmin(AdminImageMixin, InlineActionsMixin, admin.TabularInline):
    model = Identity.identity.through
    extra = 0
    max_num = 0
    fields = ["get_image"]
    readonly_fields = ["get_image"]
    inline_actions = [
        "inline_create_crop"
    ]
    def inline_create_crop(self, request, obj, parent_obj=None):
        obj.entity.crop(force=True)
    inline_create_crop.short_description = "Crop"

    def get_image(self, obj):
        obj = obj.entity
        if obj.has_image():
            return mark_safe('<img style="max-width: 200px" src="%s">' % obj.image.url)
        return "No crop yet"


class EntityMatchInlineAdmin(AdminImageMixin, InlineActionsMixin, admin.TabularInline):
    model = IdentityMatch
    extra = 0
    max_num = 0
    fields = [
        "get_image",
        "euclidean_distance"
    ]
    readonly_fields = [
        "get_image",
        "euclidean_distance"
    ]
    can_delete = False  # this will be performed though the inline action
    inline_actions = []
    
    def get_inline_actions(self, request, obj=None):
        actions = [
            "inline_create_crop"
        ]
        if not obj.identity.identity.filter(id=obj.entity_id).exists():
            actions += [
                'inline_add_to_identity',
                'inline_exclude_match'
            ]
        return actions

    def inline_create_crop(self, request, obj, parent_obj=None):
        obj.entity.crop(force=True)
    inline_create_crop.short_description = "Crop"

    def inline_exclude_match(self, request, obj, parent_obj=None):
        # obj will be the matchs.through
        parent_obj.excluded.add(obj.entity)
        obj.delete()
    inline_exclude_match.short_description = "Remove"

    def inline_add_to_identity(self, request, obj, parent_obj=None):
        # obj will be the matchs.through
        parent_obj.identity.add(obj.entity)
    inline_add_to_identity.short_description = "Add to identity"

    def get_image(self, obj):
        obj = obj.entity
        if obj.has_image():
            return mark_safe('<img style="max-width: 200px" src="%s">' % obj.image.url)
        return "No crop yet"


class IdentityAdmin(AdminImageMixin, InlineActionsModelAdminMixin, admin.ModelAdmin):
    list_display = [
        'pk',
        'name'
    ]
    fields = [
        "name",
        "identity",
        "render_inline_actions"
    ]
    inlines = [
        EntityIdentityInlineAdmin,
        EntityMatchInlineAdmin,
    ]
    inline_actions = [
        'inline_find_similars'
    ]
    actions = [
        'find_similars'
    ]
    # inline actions
    def inline_find_similars(self, request, obj, parent_obj=None):
        matchs = obj.find_similars()
        messages.info(request, "Found %s similars" % len(matchs))
    inline_find_similars.short_description = "Find Similars"

    # actions
    def find_similars(self, request, queryset):
        for identity in queryset:
            identity.find_similars()


admin.site.register(Identity, IdentityAdmin)
