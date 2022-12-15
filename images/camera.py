from datetime import datetime
import cv2
from images.models import ImageFile
from django.utils import timezone
from django.core.files.storage import FileSystemStorage  # 파일저장


class VideoCamera(object):
    def __init__(self):
        self.video = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    def __del__(self):
        self.video.release()

    # This function is used in views
    def get_frame(self):
        success, image = self.video.read()

        frame_flip = cv2.flip(image, 1)
        ret, jpeg = cv2.imencode('.jpg', frame_flip)
        return jpeg.tobytes()


class SaveCamera(object):
    def __init__(self):
        self.video = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    def __del__(self):
        self.video.release()

    # This function is used in views
    def save(self):
        success, image = self.video.read()
        self.video.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        print("save 저장 시작")
        cv2.imwrite('./media/webcam.jpg', image)

        imagesFile = ImageFile()
        imagesFile.title = "webcam.jpg"
        imagesFile.pubDate = datetime.now(tz=timezone.utc)
        imagesFile.save()
        return imagesFile.title


class FileSave(object):

    def save(self, request):
        file = request.FILES['file']
        fs = FileSystemStorage()
        fileName=fs.save("food.jpg", file)
        print("저장Name", fileName)

        imagesFile = ImageFile()
        imagesFile.title = fileName
        imagesFile.pubDate = datetime.now(tz=timezone.utc)
        imagesFile.save()

        return fileName
