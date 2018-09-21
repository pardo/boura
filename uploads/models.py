import os
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

    def pardofy(self, save=False):
        def distancePoints(p1, p2):
            import math
            return math.sqrt(math.pow(p1[0] - p2[0], 2) + math.pow(p1[1] - p2[1], 2))

        def scale(a, s):
            return map(lambda x: int(x*s), a)
        faces = self.entity_set.filter(type="face")
        if not faces.exists():
            return

        upload_im = Image.open(self.image.path)
        
        pardoObj = Pardo.objects.order_by("?")[0]
        pardo = Image.open(pardoObj.image.path)
        pardo_right_eye = pardoObj.get_right_eye_position()
        pardo_left_eye = pardoObj.get_left_eye_position()
        pardo_mouth = pardoObj.get_mouth_position()
        pardos_eye_distance = distancePoints(pardo_right_eye, pardo_left_eye)
        pardos_right_eye_to_mouth_distance = distancePoints(pardo_right_eye, pardo_mouth)

        for face_entity in faces:
            angle = face_entity.get_face_angle()
            right_eye = face_entity.get_right_eye_position()
            left_eye = face_entity.get_left_eye_position()
            mouth = face_entity.get_mouth_position()
            eye_distance = distancePoints(right_eye, left_eye)
            mouse_to_eye_distance = distancePoints(right_eye, mouth)
            right_eye = scale(right_eye, 1)
            # this will be used to scale pardo image to fit the face eye distance
            eye_distance_scale = eye_distance / pardos_eye_distance
            mouth_scale = mouse_to_eye_distance / (pardos_right_eye_to_mouth_distance * eye_distance_scale)

            pardo_right_eye_scaled = scale(pardo_right_eye, eye_distance_scale)
            pardo_resized_scale = scale(pardo.size, eye_distance_scale)
            pardo_resized = pardo.resize(
                pardo_resized_scale[:],
                resample=Image.BILINEAR,
            )
            # resize the shape a bit on the Y axis so it matches the mouse position
            pardo_resized_scale[1] = int(pardo_resized_scale[1] * mouth_scale)
            pardo_right_eye_scaled[1] = int(pardo_right_eye_scaled[1] * mouth_scale)
            pardo_resized = pardo.resize(
                pardo_resized_scale[:],
                resample=Image.BILINEAR,
            )
            pardo_rotated = pardo_resized.rotate(
                -angle,
                resample=Image.BILINEAR,
                center=pardo_right_eye_scaled
            )
            paste_position = [
                right_eye[0] - pardo_right_eye_scaled[0],
                right_eye[1] - pardo_right_eye_scaled[1]
            ]
            if pardo_rotated.mode != "RGBA":
                pardo_rotate_alpha = Image.new("L",  pardo_rotated.size, color=150)
                upload_im.paste(pardo_rotated, paste_position, mask=pardo_rotate_alpha)
            else:
                upload_im.paste(pardo_rotated, paste_position, mask=pardo_rotated)
        if save:
            upload_path = os.path.split(upload_im.filename)
            filename = os.path.join(
                upload_path[0],
                "pardofy-%s" % upload_path[1],
            )
            with open(filename, "w") as image_file:
                upload_im.save(image_file, "JPEG")
        else:
            upload_im.show()

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

    def get_identities(self):
        from identity.models import Identity
        return Identity.objects.filter(
            id__in=self.identity_matchs_set.values_list("identity_id")
        )

    def get_mouth_position(self):
        mouth = self.meta["landmark_68"][48:68]
        mouth_avg = reduce(lambda b, a: [a[0] + b[0], a[1] + b[1]], mouth)
        mouth_avg[0] = mouth_avg[0] / 20.0
        mouth_avg[1] = mouth_avg[1] / 20.0
        return mouth_avg

    def get_left_eye_position(self):
        left_eye = self.meta["landmark_68"][42:48]
        left_eye_avg = reduce(lambda b, a: [a[0] + b[0], a[1] + b[1]], left_eye)
        left_eye_avg[0] = left_eye_avg[0] / 6.0
        left_eye_avg[1] = left_eye_avg[1] / 6.0
        return left_eye_avg
    
    def get_right_eye_position(self):
        right_eye = self.meta["landmark_68"][36:42]
        right_eye_avg = reduce(lambda b, a: [a[0] + b[0], a[1] + b[1]], right_eye)
        right_eye_avg[0] = right_eye_avg[0] / 6.0
        right_eye_avg[1] = right_eye_avg[1] / 6.0
        return right_eye_avg

    def get_face_angle(self):
        # keep in mind that is the right eye of the person
        # so if you are looking at the image the right eye will be placed on the left
        left_eye_avg = self.get_left_eye_position()
        right_eye_avg = self.get_right_eye_position()
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



class Pardo(models.Model):
    """
        this should be an image with only one face
    """
    date_added = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    image = ImageField(upload_to='pardos/%Y-%m-%d/')
    meta = JSONField(default={}, blank=True)

    def get_mouth_position(self):
        mouth = self.meta["landmark_68"][48:68]
        mouth_avg = reduce(lambda b, a: [a[0] + b[0], a[1] + b[1]], mouth)
        mouth_avg[0] = mouth_avg[0] / 20.0
        mouth_avg[1] = mouth_avg[1] / 20.0
        return mouth_avg

    def get_left_eye_position(self):
        left_eye = self.meta["landmark_68"][42:48]
        left_eye_avg = reduce(lambda b, a: [a[0] + b[0], a[1] + b[1]], left_eye)
        left_eye_avg[0] = left_eye_avg[0] / 6.0
        left_eye_avg[1] = left_eye_avg[1] / 6.0
        return left_eye_avg
    
    def get_right_eye_position(self):
        right_eye = self.meta["landmark_68"][36:42]
        right_eye_avg = reduce(lambda b, a: [a[0] + b[0], a[1] + b[1]], right_eye)
        right_eye_avg[0] = right_eye_avg[0] / 6.0
        right_eye_avg[1] = right_eye_avg[1] / 6.0
        return right_eye_avg

    def get_face_angle(self):
        # keep in mind that is the right eye of the person
        # so if you are looking at the image the right eye will be placed on the left
        left_eye_avg = self.get_left_eye_position()
        right_eye_avg = self.get_right_eye_position()
        angle = math.atan2(left_eye_avg[1] - right_eye_avg[1], left_eye_avg[0] - right_eye_avg[0])
        return math.degrees(angle)

    def process_dlib(self):
        im = Image.open(self.image.path)
        files = {'photo': self.image.file }
        if im.mode == "RGBA":
            im = im.convert("RGB")
        
            image_file = BytesIO()
            im.save(image_file, "JPEG")
            image_file.seek(0)
            # need to conver to RGB
            files = {'photo': image_file }

        r = requests.post(settings.DLIB_SERVICE_HOST + "/faces-descriptors", files=files)
        response = r.json()

        for re in response:
            self.meta = {}
            self.meta["top"] = re["top"]
            self.meta["right"] = re["right"]
            self.meta["bottom"] = re["bottom"]
            self.meta["left"] = re["left"]
            self.meta["landmark_68"] = re["landmark_68"]
            self.meta["face_descriptor"] = re["face_descriptor"]

        self.save()

    def crop(self):
        right_eye = self.get_right_eye_position()
        left_eye = self.get_left_eye_position()
        center = [
            int(right_eye[0]), int(right_eye[1])
        ]
        im = Image.open(self.image.path)
        region = im.rotate(
            self.get_face_angle(),
            center=center
        )
        image_file = BytesIO()
        region.save(image_file, "PNG")
        image_file.seek(0)
        self.image.save(
            "%s_%s.png" % (self.id, datetime.datetime.today().isoformat()), File(image_file)
        )