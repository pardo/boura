from __future__ import absolute_import
import math
from django.db import models
from django.core.urlresolvers import reverse

def euclidean_distance(vector1, vector2):
    """
    calculate the euclidean distance
    :param vector1:
    :param vector2:
    :return:
    """
    dist = [(a - b)**2 for a, b in zip(vector1, vector2)]
    dist = math.sqrt(sum(dist))
    return dist


class IdentityMatch(models.Model):
    entity = models.ForeignKey("uploads.Entity", related_name="identity_matchs_set")
    identity = models.ForeignKey("identity.Identity", related_name="matchs")
    euclidean_distance = models.FloatField(default=0)

    class Meta:
        unique_together = (
            "entity",
            "identity"
        )

class Identity(models.Model):
    name = models.CharField(max_length=100, default="", blank=True)
    excluded = models.ManyToManyField("uploads.Entity", related_name="identity_excluded_set", blank=True)
    identity = models.ManyToManyField("uploads.Entity", related_name="identity_source_set", blank=True)

    def get_admin_change_url(self):
        return reverse("admin:%s_%s_change" %(self._meta.app_label, self._meta.model_name), args=(self.id,))

    def find_similars(self, max_distance=0.6):
        from uploads.models import Entity

        excluded_ids = list(self.matchs.values_list("entity_id", flat=True))
        excluded_ids += list(self.excluded.values_list("id", flat=True))
        # excluded_ids += list(self.identity.values_list("id", flat=True))

        entities = Entity.objects\
            .filter(type="face")\
            .exclude(id__in=excluded_ids)

        sources = []
        for entity in self.identity.all():
            sources.append(entity.meta["face_descriptor"])

        matchs = []
        
        for e in entities:
            distance = 0
            for source in sources:
                distance += euclidean_distance(source, e.meta["face_descriptor"])
            avg_distance = distance / len(sources)
            if avg_distance < max_distance:
                matchs.append(e)
                IdentityMatch.objects.create(
                    identity=self,
                    entity=e,
                    euclidean_distance=avg_distance
                )
        return matchs

    def __str__(self):
        return "Identity %s" % self.id