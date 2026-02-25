from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenObtainPairView
from . import views

router = SimpleRouter()
router.register('cards', views.CardModelViewSet)
router.register('decks', views.DeckModelViewSet)
router.register('waitlist', views.WaitlistModelViewSet)
router.register('users', views.UsersModelViewSet)

urlpatterns = [
	path(r'auth/signin/', TokenObtainPairView.as_view()),
	path(r'auth/signup/', csrf_exempt(views.AuthModelViewSet.as_view({ 'post': 'signup' }))),
	path(r'users/add_friend/', views.UsersRelationshipModelViewSet.as_view({ 'post': 'create' })),
	path(r'users/get_friends/', views.UsersRelationshipModelViewSet.as_view({ 'get': 'list' })),
	path(r'users/accept_friend_request/', views.UsersRelationshipModelViewSet.as_view({ 'post': 'accept_friend_request' })),
	path(r'users/reject_friend_request/', views.UsersRelationshipModelViewSet.as_view({ 'post': 'reject_friend_request' })),
]

urlpatterns += router.urls
