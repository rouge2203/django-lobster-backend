from django.urls import path
from . import views

urlpatterns = [
    path('greetings', views.greetings, name='greetings'),
    path('greetings-email', views.greetings_email, name='greetings_email'),
]
