import math
from django.db import models
from uploads.models import Entity

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


class Identity(models.Model):
    matchs = models.ManyToManyField(Entity, related_name="identity_matchs_set")
    excluded = models.ManyToManyField(Entity, related_name="identity_excluded_set")
    identity = models.ManyToManyField(Entity, related_name="identity_source_set")

    def find_similar(self, max_distance=0.6):
        entities = Entity.objects\
            .filter(type="face")\
            .exclude(id__in=list(self.matchs.values_list("id")) + list(self.excluded.values_list("id")))

        sources = []
        for entity in self.identity.all():
            sources.append(entity.meta["face_descriptor"])

        matchs = []
        for e in entities:
            distance = 0
            for source in sources:
                distance += euclidean_distance(source, e.meta["face_descriptor"])
            if distance / len(sources) < max_distance:
                matchs.append(e)
        self.matchs.add(*matchs)

        return matchs

    def __str__(self):
        return "Identity %s" % self.id