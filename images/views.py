from django.shortcuts import render, redirect
from django.http import HttpResponse, StreamingHttpResponse
from django.core.files.storage import FileSystemStorage  # 파일저장
from .camera import VideoCamera
from .camera import SaveCamera
from .camera import FileSave
from .vegan import vegn_main
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def index(request):
    return render(request, "images/index.html")

def example(request) :
    return render(request, "images/example.html")

def webcam(request):
    return render(request, "images/webcam.html")


def upload(request):
    return render(request, "images/fileupload.html")


def food_analysis(request):
    veganInfo = vegn_main("foodPoto.jpg")
    print('호출', veganInfo)
    response = HttpResponse()
    response.write("<h1>Welcome</h1>")
    response.write("<p>This is my first Django. </p>")

    return render(request, "images/foodanalysis.html", veganInfo)


def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


@csrf_exempt
def save_cam(request):
    print("save_cam 호출")
    frame = SaveCamera()
    fileName = frame.save()
    context = {"fileName": fileName}
    return render(request, "images/foodanalysis.html", context)


# Method for laptop camera
def video_feed(request):
    return StreamingHttpResponse(gen(VideoCamera()), content_type='multipart/x-mixed-replace; boundary=frame')


def file_upload(request):

    fileName = FileSave().save(request)
    context = {"fileName":fileName}
    return render(request, "images/foodanalysis.html", context)


@csrf_exempt
def vegan_analysis(request):
    print("vegan_analysis 호출")
    imgFile = ""

    if 'imgFile' in request.POST:
        imgFile = request.POST['imgFile']
        print("imgFILE : ", imgFile)
    # 공백이 아닌 경우
    answer = ""
    if imgFile != "":
        # method호출
        answer = vegn_main(imgFile)
        print('호출', answer)
        if answer == False :
            answer = {"FAIL": "원재료 성분표가 포함된 이미지가 아닙니다."}
            return JsonResponse(answer)
    else:
        answer = {"FAIL": "이미지 파일이 없습니다."}

    return JsonResponse(answer)
