from django.urls import path
from . import views
from . import fcprosoccertryouts_views

urlpatterns = [
    path('greetings', views.greetings, name='greetings'),
    path('greetings-email', views.greetings_email, name='greetings_email'),
    path('fcprosoccertryouts/submit-application', fcprosoccertryouts_views.submit_application, name='submit_application'),
]
