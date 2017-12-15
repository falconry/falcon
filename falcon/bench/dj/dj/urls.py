from django.conf.urls import url
from hello import views


urlpatterns = [
    url(r'^hello/(?P<account_id>[0-9]+)/test$', views.hello)
]
