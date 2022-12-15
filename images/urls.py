from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name='index'),
    path('video_feed', views.video_feed, name='video_feed'),
    path('file_upload', views.file_upload, name='file_upload'),
    path('webcam', views.webcam, name='webcam'),
    path('food_analysis', views.food_analysis, name='food_analysis'),
    path('upload', views.upload, name='upload'),
    path('save_cam', views.save_cam, name='save_cam'),
    path('vegan_analysis', views.vegan_analysis, name='vegan_analysis'),
    path('example', views.example, name='example')


]
