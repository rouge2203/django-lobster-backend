from django.urls import path
from . import views
from . import fcprosoccertryouts_views
from . import tellos_views

urlpatterns = [
    path('greetings', views.greetings, name='greetings'),
    path('greetings-email', views.greetings_email, name='greetings_email'),
    path('fcprosoccertryouts/submit-application', fcprosoccertryouts_views.submit_application, name='submit_application'),
    path('tellos/confirm-reservation', tellos_views.confirm_reservation, name='confirm_reservation'),
    path('tellos/send-test-email', tellos_views.send_test_email, name='send_test_email'),
    path('tellos/notify-new-reto', tellos_views.notify_new_reto, name='notify_new_reto'),
]
