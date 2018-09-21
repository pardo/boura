import json
import os
import math
import requests
from PIL import ImageDraw
from PIL import Image
from PIL import ImageFilter
from io import BytesIO
from functools import reduce

DLIB_SERVICE_HOST = "http://localhost:8080"


def get_landmark_68_data(landmark_68):
    pardo_right_eye = get_right_eye_position(landmark_68)
    pardo_left_eye = get_left_eye_position(landmark_68)
    pardo_mouth = get_mouth_position(landmark_68)
    return {
        "right_eye": pardo_right_eye,
        "left_eye": pardo_left_eye,
        "mouth": pardo_mouth,
        "nose_angle": get_nose_angle(landmark_68),
        "eye_distance": distancePoints(pardo_right_eye, pardo_left_eye),
        "right_eye_to_mouth_distance": distancePoints(pardo_right_eye, pardo_mouth)
    }


def load_image_data(path):
    print("Load image data %s" % path)
    try:
        image = Image.open(path)
    except IOError:
        return []
    data = []
    for pard_dlib_data in process_dlib(image):
        data.append({
            "path": path,
            "image": image,
            "dlib_data": pard_dlib_data
        })
    return data


def process_dlib(image):
    if image.mode == "RGBA":
        image = image.convert("RGB")
    image_file = BytesIO()
    image.save(image_file, "JPEG")
    image_file.seek(0)
    # need to conver to RGB
    files = {'photo': image_file}
    r = requests.post(DLIB_SERVICE_HOST + "/faces-descriptors", files=files)
    return r.json()

def distancePoints(p1, p2):
    return math.sqrt(math.pow(p1[0] - p2[0], 2) + math.pow(p1[1] - p2[1], 2))

def scale(a, s):
    return list(map(lambda x: int(x*s), a))

def get_mouth_position(landmark_68):
    mouth = landmark_68[48:68]
    mouth_avg = reduce(lambda b, a: [a[0] + b[0], a[1] + b[1]], mouth)
    mouth_avg[0] = mouth_avg[0] / 20.0
    mouth_avg[1] = mouth_avg[1] / 20.0
    return mouth_avg

def get_left_eye_position(landmark_68):
    left_eye = landmark_68[42:48]
    left_eye_avg = reduce(lambda b, a: [a[0] + b[0], a[1] + b[1]], left_eye)
    left_eye_avg[0] = left_eye_avg[0] / 6.0
    left_eye_avg[1] = left_eye_avg[1] / 6.0
    return left_eye_avg

def get_right_eye_position(landmark_68):
    right_eye = landmark_68[36:42]
    right_eye_avg = reduce(lambda b, a: [a[0] + b[0], a[1] + b[1]], right_eye)
    right_eye_avg[0] = right_eye_avg[0] / 6.0
    right_eye_avg[1] = right_eye_avg[1] / 6.0
    return right_eye_avg

def get_face_angle(landmark_68):
    # keep in mind that is the right eye of the person
    # so if you are looking at the image the right eye will be placed on the left
    left_eye_avg = get_left_eye_position(landmark_68)
    right_eye_avg = get_right_eye_position(landmark_68)
    angle = math.atan2(left_eye_avg[1] - right_eye_avg[1], left_eye_avg[0] - right_eye_avg[0])
    return math.degrees(angle)

def get_nose_angle(landmark_68):
    angle = math.atan2(
        landmark_68[27][1] - landmark_68[30][1],
        landmark_68[27][0] - landmark_68[30][0]
    )
    noseAngleDeg = math.degrees(angle)
    angle = math.atan2(
        landmark_68[27][1] - landmark_68[33][1],
        landmark_68[27][0] - landmark_68[33][0]
    )
    noseToBottomAngleDeg = math.degrees(angle)
    offset = 270 - noseToBottomAngleDeg
    return offset + noseAngleDeg

def get_best_pardo(pardos, nose_angle):
    selected = None
    selected_distance = 1000
    for pardo_data in pardos:
        current_distance = abs(pardo_data["nose_angle"] - nose_angle)
        if current_distance < selected_distance:
            selected = pardo_data
            selected_distance = current_distance
    print(selected["path"])
    return selected

def get_face_polygon(landmark_68):
    chin_middle = [
        (landmark_68[0][0] + landmark_68[16][0]) / 2,
        (landmark_68[0][1] + landmark_68[16][1]) / 2,
    ]
    ox = chin_middle[0]
    oy = chin_middle[1]
    
    points = landmark_68[0:17]
    points = list(map(lambda p: [
        (math.cos(math.pi) * (p[0]-ox) - math.sin(math.pi) * (p[1]-oy) + ox),
        (math.sin(math.pi) * (p[0]-ox) + math.cos(math.pi) * (p[1]-oy) + oy)
    ], points[0:5] + points[12:17]))
    points += landmark_68[0:17]
    # we need integer and tuples
    points = map(lambda p: (int(p[0]), int(p[1])), points)
    return list(points)


def auto_crop_face(image_data, add_alpha=True):
    points = get_face_polygon(image_data["dlib_data"]["landmark_68"])
    # get bounding box
    left = min(map(lambda x: x[0], points))
    right = max(map(lambda x: x[0], points))
    top = min(map(lambda x: x[1], points))
    bottom = max(map(lambda x: x[1], points))

    size = max([right - left, bottom - top])
    left = max([left - size * .3, 0])
    right = min([right + size * .3, image_data["image"].size[0]])
    top = max([top - size * .3, 0])
    bottom = min([bottom + size * .3, image_data["image"].size[1]])

    image = image_data["image"].copy().crop([left, top, right, bottom])
    image_data["top"] = top
    image_data["bottom"] = bottom
    image_data["right"] = right
    image_data["left"] = left
    # translate points
    points = list(map(lambda x: (x[0] - left, x[1] - top), points))
    image_data["dlib_data"]["landmark_68"] = list(map(lambda x: (x[0] - left, x[1] - top), image_data["dlib_data"]["landmark_68"]))
    # facial data
    image_data.update(get_landmark_68_data(image_data["dlib_data"]["landmark_68"]))
   
    if not add_alpha:
        image_data["image"] = image
        return image_data

    # alpha blending blured
    alpha_image = Image.new("L",  image.size[:], color=0)
    alpha_draw = ImageDraw.Draw(alpha_image)
    alpha_draw.polygon(points, fill=255)
    alpha_image = alpha_image.filter(ImageFilter.GaussianBlur(
        max(image_data["image"].size) * 0.013
    ))
    # scale down the blur alpha
    # alpha_image_scale = Image.new("L",  scale(image.size[:], 1.1), color=0)
    # alpha_image_scale.paste(alpha_image, scale(image.size[:], 0.05))
    # alpha_image_scale = alpha_image_scale.resize(image.size[:])
    # image.putalpha(alpha_image_scale)
    image = image.convert("RGBA")
    image.putalpha(alpha_image)
    image_data["image"] = image

    return image_data

def blur_face_image(image, face_dlib_data):
    points = get_face_polygon(face_dlib_data["landmark_68"])
    top = min(map(lambda p: p[1], points))
    top = int(top * 0.9)
    left = int(face_dlib_data["left"] * 0.9)
    right = int(face_dlib_data["right"] * 1.1)
    bottom = int(face_dlib_data["bottom"] * 1.1)
    translated_points = list(map(lambda p: (p[0] - left, p[1] - top), points))
    # face crop blured
    face_blur = image.crop(
        [left, top, right, bottom]
    ).filter(ImageFilter.GaussianBlur(10))
    # alpha blending blured
    face_blur_alpha = Image.new("L",  face_blur.size, color=0)
    face_blur_alpha_draw = ImageDraw.Draw(face_blur_alpha)
    face_blur_alpha_draw.polygon(
        translated_points,
        fill=250
    )
    face_blur_alpha = face_blur_alpha.filter(ImageFilter.GaussianBlur(10))
    image.paste(face_blur, [left, top], mask=face_blur_alpha)
    return image



def pardofy(filename, output_dir, pardos):
    print("-"*99)
    print(filename)
    upload_im = Image.open(filename)
    faces_data = process_dlib(upload_im)

    for face_dlib_data in faces_data:
        angle = get_face_angle(face_dlib_data["landmark_68"])
        right_eye = get_right_eye_position(face_dlib_data["landmark_68"])
        left_eye = get_left_eye_position(face_dlib_data["landmark_68"])
        mouth = get_mouth_position(face_dlib_data["landmark_68"])
        nose_angle = get_nose_angle(face_dlib_data["landmark_68"])
        eye_distance = distancePoints(right_eye, left_eye)
        mouse_to_eye_distance = distancePoints(right_eye, mouth)
        # convert to int
        right_eye = scale(right_eye, 1)

        pardo_data = get_best_pardo(pardos, nose_angle)

        # this will be used to scale pardo image to fit the face eye distance
        eye_distance_scale = eye_distance / pardo_data["eye_distance"]
        mouth_scale = mouse_to_eye_distance / (pardo_data["right_eye_to_mouth_distance"] * eye_distance_scale)

        pardo_right_eye_scaled = scale(pardo_data["right_eye"], eye_distance_scale)
        pardo_resized_scale = scale(pardo_data["image"].size, eye_distance_scale)
        
        # resize the shape a bit on the Y axis so it matches the mouse position
        pardo_resized_scale[1] = int(pardo_resized_scale[1] * mouth_scale)
        pardo_right_eye_scaled[1] = int(pardo_right_eye_scaled[1] * mouth_scale)
        
        pardo_resized = pardo_data["image"].resize(
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

        blur_face_image(upload_im, face_dlib_data)

        if pardo_rotated.mode != "RGBA":
            pardo_rotate_alpha = Image.new("L",  pardo_rotated.size, color=150)
            upload_im.paste(pardo_rotated, paste_position, mask=pardo_rotate_alpha)
        else:
            upload_im.paste(pardo_rotated, paste_position, mask=pardo_rotated)

    if len(faces_data):
        upload_path = os.path.split(filename)
        filename = os.path.join(
            output_dir,
            "pardofy-%s" % upload_path[1],
        )
        with open(filename, "wb") as image_file:
            upload_im.convert("RGB").save(image_file, "JPEG")


def pardofy_cv(filename, output_dir, pardos):
    print("-"*99)
    print(filename)
    upload_im = Image.open(filename)
    faces_data = process_dlib(upload_im)

    if len(faces_data) == 0:
        return

    for face_dlib_data in faces_data:
        blur_face_image(upload_im, face_dlib_data)

    upload_path = os.path.split(filename)
    filename = os.path.join(output_dir, "base.jpg")
    with open(filename, "wb") as image_file:
        upload_im.convert("RGB").save(image_file, "JPEG")

    faces_photo = Image.new("RGBA",  upload_im.size)
    for face_dlib_data in faces_data:
        angle = get_face_angle(face_dlib_data["landmark_68"])
        right_eye = get_right_eye_position(face_dlib_data["landmark_68"])
        left_eye = get_left_eye_position(face_dlib_data["landmark_68"])
        mouth = get_mouth_position(face_dlib_data["landmark_68"])
        nose_angle = get_nose_angle(face_dlib_data["landmark_68"])
        eye_distance = distancePoints(right_eye, left_eye)
        mouse_to_eye_distance = distancePoints(right_eye, mouth)
        # convert to int
        right_eye = scale(right_eye, 1)

        pardo_data = get_best_pardo(pardos, nose_angle)

        # this will be used to scale pardo image to fit the face eye distance
        eye_distance_scale = eye_distance / pardo_data["eye_distance"]
        mouth_scale = mouse_to_eye_distance / (pardo_data["right_eye_to_mouth_distance"] * eye_distance_scale)

        pardo_right_eye_scaled = scale(pardo_data["right_eye"], eye_distance_scale)
        pardo_resized_scale = scale(pardo_data["image"].size, eye_distance_scale)
        
        # resize the shape a bit on the Y axis so it matches the mouse position
        pardo_resized_scale[1] = int(pardo_resized_scale[1] * mouth_scale)
        pardo_right_eye_scaled[1] = int(pardo_right_eye_scaled[1] * mouth_scale)
        
        pardo_resized = pardo_data["image"].resize(
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

        blur_face_image(upload_im, face_dlib_data)
        faces_photo.paste(pardo_rotated, paste_position, mask=pardo_rotated)

    faces_filename = os.path.join(output_dir, "faces.png")
    with open(faces_filename, "wb") as image_file:
        faces_photo.save(image_file, "PNG")

    out_filename = os.path.join(output_dir, "pardofy-%s.jpg" % upload_path[1],)
    seemless(faces_filename, filename, out_filename)

def auto_pardo(input_folder_path, output_folder_path=None, add_alpha=True):
    if output_folder_path is None:
        output_folder_path = os.path.join(input_folder_path, 'crops')
        if not os.path.exists(output_folder_path):
            os.makedirs(output_folder_path)
    for filename in os.listdir(input_folder_path):
        photo_path = os.path.join(input_folder_path, filename)
        for idx, image_data in enumerate(load_image_data(photo_path)):
            image_data = auto_crop_face(image_data, add_alpha)
            
            filename_photo = os.path.join(output_folder_path, "face-%s-%s-.png" % (filename, idx))
            with open(filename_photo, "wb") as image_file:
                image_data["image"].save(image_file, "PNG")
            del image_data["image"]
            filename_json = os.path.join(output_folder_path, "face-%s-%s-.json" % (filename, idx))
            with open(filename_json, "w") as file:
                json.dump(image_data, file)


def load_pardos(folder_path):
    pardos =[]
    for filename in os.listdir(folder_path):
        if filename.startswith("face-") and filename.endswith(".png"):
            photo_path = os.path.join(folder_path, filename)
            photo_data_path = os.path.join(folder_path, filename.replace(".png", ".json"))
            with open(photo_data_path, "r") as file:
                data = json.load(file)
            data["image"] = Image.open(photo_path)
            pardos.append(data)
    return pardos


def work(pardos_paths, input_path, output_path):
    pardos = []
    for path in pardos_paths:
        pardos += load_pardos(path)
    for destiny_photo_path in os.listdir(input_path):
        filename = os.path.join(input_path, destiny_photo_path)
        if "pardofy" in filename:
            continue
        pardofy_cv(filename, output_path, pardos)


def load_image_array(image):
    alpha_array = []
    image_array = []
    for y in range(image.height):
        row = []
        alpha = []
        for x in range(image.width):
            p = list(image.getpixel((x,y)))
            color = p[:3]
            color.reverse()
            alpha.append(p[3],)
            row.append(tuple(color))
        image_array.append(tuple(row))
        alpha_array.append(tuple(alpha))
    return tuple(image_array), tuple(alpha_array)


def seemless(src_path, dst_path, out_path):
    print("Seemless %s" % src_path)
    import cv2
    import numpy as np
    # Read images
    src = cv2.imread(src_path)
    mask = cv2.imread(src_path, cv2.IMREAD_UNCHANGED)[:,:,3]
    mask[0][0] = 255
    mask[0][mask.shape[1]-1] = 255
    mask[mask.shape[0]-1][0] = 255
    mask[mask.shape[0]-1][mask.shape[1]-1] = 255

    dst = cv2.imread(dst_path)
    center = tuple(scale(dst.shape, 0.5))[:2]
    output = cv2.seamlessClone(
        src, dst, mask, center, cv2.NORMAL_CLONE
    )
    # Save result
    cv2.imwrite(out_path, output)
