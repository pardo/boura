
import requests
import math
import datetime

from PIL import Image
from io import BytesIO
from django.core.files import File

from django.db import models
from django.utils import timezone
from django_common.db_fields import JSONField
from django.conf import settings
from django.core.urlresolvers import reverse

from sorl.thumbnail import ImageField


class Upload(models.Model):
    date_added = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    image = ImageField(upload_to='uploads/%Y-%m-%d/')
    darknet_processing_start = models.DateTimeField(null=True, blank=True)
    darknet_processing_end = models.DateTimeField(null=True, blank=True)
    dlib_processing_start = models.DateTimeField(null=True, blank=True)
    dlib_processing_end = models.DateTimeField(null=True, blank=True)

    @property
    def number_of_entities(self):
        return self.entity_set.count()

    def get_admin_change_url(self):
        return reverse("admin:%s_%s_change" %(self._meta.app_label, self._meta.model_name), args=(self.id,))

    def process_darknet(self, force=False):
        if self.darknet_processing_end is not None and not force:
            return
        
        self.darknet_processing_end = None
        self.darknet_processing_start = timezone.now()
        self.save()
        files = {'photo': self.image.file }
        r = requests.post(settings.DARKENET_SERVICE_HOST + "/yolo", files=files)
        response = r.json()
        for re in response:
            entity = Entity()
            entity.upload = self
            entity.type = re["class"]
            entity.top = re["top"]
            entity.right = re["right"]
            entity.bottom = re["bottom"]
            entity.left = re["left"]
            entity.score = re["probability"]
            entity.save()

        self.darknet_processing_end = timezone.now()
        self.save()

    def process_dlib(self, force=False):
        if self.dlib_processing_end is not None and not force:
            return

        self.dlib_processing_end = None
        self.dlib_processing_start = timezone.now()
        self.save()
        files = {'photo': self.image.file }
        r = requests.post(settings.DLIB_SERVICE_HOST + "/faces-descriptors", files=files)
        response = r.json()

        for re in response:
            entity = Entity()
            entity.upload = self
            entity.type = re["class"]
            entity.top = re["top"]
            entity.right = re["right"]
            entity.bottom = re["bottom"]
            entity.left = re["left"]
            entity.score = -1
            entity.meta["landmark_68"] = re["landmark_68"]
            entity.meta["face_descriptor"] = re["face_descriptor"]
            entity.save()

        self.dlib_processing_end = timezone.now()
        self.save()

    def get_thumbnail(self):
        from sorl.thumbnail import get_thumbnail
        return get_thumbnail(self.image, '300', crop='center', quality=70)

    def get_view_url(self):
        return reverse("view_upload") + "?upload=%s" % self.id

    def __str__(self):
        return "Upload %s" % self.id


class Entity(models.Model):
    date_added = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    upload = models.ForeignKey(Upload)
    image = ImageField(upload_to='crops/%Y-%m-%d/', null=True, blank=True)
    type = models.CharField(max_length=100)
    score = models.FloatField(default=0)
    top = models.PositiveIntegerField(default=0)
    right = models.PositiveIntegerField(default=0)
    bottom = models.PositiveIntegerField(default=0)
    left = models.PositiveIntegerField(default=0)
    meta = JSONField(default={}, blank=True)

    @classmethod
    def test(self):
        for e in Entity.objects.all():
            im = Image.open(e.image.path)
            im_10 = im.resize((10, 10), Image.ANTIALIAS)
            im_20 = im.resize((20, 20), Image.ANTIALIAS)
            im_30 = im.resize((30, 30), Image.ANTIALIAS)
            e.meta["histogram_10"] = im_10.histogram()
            e.meta["histogram_20"] = im_20.histogram()
            e.meta["histogram_30"] = im_30.histogram()
            e.save()
            print(e.id)

    def test_2(self):
        from identity.models import euclidean_distance
        for e in Entity.objects.all():
            print(self.id, e.id, euclidean_distance(self.meta["histogram_30"], e.meta["histogram_30"]))

    def get_face_angle(self):
        # keep in mind that is the right eye of the person
        # so if you are looking at the image the right eye will be placed on the left
        right_eye = self.meta["landmark_68"][36:42]
        left_eye = self.meta["landmark_68"][42:48]
        left_eye_avg = reduce(lambda b, a: [a[0] + b[0], a[1] + b[1]], left_eye)
        left_eye_avg[0] = left_eye_avg[0] / 6.0
        left_eye_avg[1] = left_eye_avg[1] / 6.0

        right_eye_avg = reduce(lambda b, a: [a[0] + b[0], a[1] + b[1]], right_eye)
        right_eye_avg[0] = right_eye_avg[0] / 6.0
        right_eye_avg[1] = right_eye_avg[1] / 6.0
        angle = math.atan2(left_eye_avg[1] - right_eye_avg[1], left_eye_avg[0] - right_eye_avg[0])

        return math.degrees(angle)

    def has_image(self):
        try:
            if self.image.path:
                return True
        except ValueError:
            pass

        return False

    def _show(self):
        if not self.has_image():
            self.crop()

        im = Image.open(self.image.path)
        im.show()

    def crop(self, scale=1, force=False):
        if self.has_image() and not force:
            return

        if self.type == "face" and scale == 1:
            scale = 1.9
        # 1.4 means 20% more on each size
        size_x = self.right - self.left
        size_y = self.bottom - self.top

        size_x = ((size_x * scale) - size_x) / 2.0
        size_y = ((size_y * scale) - size_y) / 2.0

        top = int(self.top - size_y)
        bottom = int(self.bottom + size_y)
        left = int(self.left - size_x)
        right = int(self.right + size_x)

        top = max(top, 0)
        bottom = min(bottom, self.upload.image.height)
        left = max(left, 0)
        right = min(right, self.upload.image.width)

        im = Image.open(self.upload.image.path)

        box = (left, top, right, bottom)
        if self.type == "face":
            region = im.rotate(
                self.get_face_angle(),
                center=[(left + right) / 2.0, (top + bottom) / 2.0]
            ).crop(box)
        else:
            region = im.crop(box)

        image_file = BytesIO()
        region.save(image_file, "JPEG")
        image_file.seek(0)
        
        self.image.save(
            "%s_%s_%s.jpg" % (self.type, self.id, datetime.datetime.today().isoformat()), File(image_file)
        )

    def __str__(self):
        return "Entity %s" % self.id