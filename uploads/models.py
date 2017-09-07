
import requests

from PIL import Image
from io import BytesIO
from django.core.files import File

from django.db import models
from django.utils import timezone
from django_common.db_fields import JSONField
from django.conf import settings

from sorl.thumbnail import ImageField


class Upload(models.Model):
    date_added = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    image = ImageField(upload_to='uploads/%Y-%m-%d/')
    darknet_processing_start = models.DateTimeField(null=True, blank=True)
    darknet_processing_end = models.DateTimeField(null=True, blank=True)
    dlib_processing_start = models.DateTimeField(null=True, blank=True)
    dlib_processing_end = models.DateTimeField(null=True, blank=True)

    def process_darknet(self):
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

    def process_dlib(self):
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

    def crop(self, scale=0, force=False):
        if self.has_image() and not force:
            return

        size_x = self.right - self.left
        size_y = self.bottom - self.top

        size_x = size_x * scale
        size_y = size_y * scale

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
        region = im.crop(box)
        image_file = BytesIO()
        region.save(image_file, "JPEG")
        image_file.seek(0)
        self.image.save("%s_%s.jpg" % (self.type, self.id), File(image_file))

    def __str__(self):
        return "Entity %s" % self.id