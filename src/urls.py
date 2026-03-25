from django.contrib import admin
from django.urls import path, include

from src.api.views.nodeinfo import NodeInfo21View, NodeInfoWellKnownView

urlpatterns = [
	path('admin/', admin.site.urls),
	path('.well-known/nodeinfo', NodeInfoWellKnownView.as_view(), name='nodeinfo-well-known'),
	path('nodeinfo/2.1', NodeInfo21View.as_view(), name='nodeinfo-2-1'),
	path('v1/', include('src.api.urls')),
]
