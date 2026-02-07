from django.urls import path
from . import views
from . import fcprosoccertryouts_views
from . import tellos_views
from . import tasks

urlpatterns = [
    path('greetings', views.greetings, name='greetings'),
    path('greetings-email', views.greetings_email, name='greetings_email'),
    path('fcprosoccertryouts/submit-application', fcprosoccertryouts_views.submit_application, name='submit_application'),
    path('tellos/confirm-reservation', tellos_views.confirm_reservation, name='confirm_reservation'),
    path('tellos/send-test-email', tellos_views.send_test_email, name='send_test_email'),
    path('tellos/notify-new-reto', tellos_views.notify_new_reto, name='notify_new_reto'),
    # Cron tasks
    path('tasks/send-24h-reminders', tasks.send_24h_reminders, name='send_24h_reminders'),
    path('tasks/send-daily-schedule', tasks.send_daily_schedule, name='send_daily_schedule'),
    path('tasks/generate-recurring-reservations', tasks.generate_recurring_reservations, name='generate_recurring_reservations'),
]
