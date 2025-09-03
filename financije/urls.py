from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('home/', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path("history/", views.history, name="history"),
    path("history/edit/<int:pk>/", views.edit_month, name="edit_month"),
    path("history/delete/<int:pk>/", views.delete_month, name="delete_month"),
    path("register/", views.register, name="register"),
    path("export_pdf/<int:pk>/", views.export_pdf, name="export_pdf"),
]
