from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Admin
    path('admin-portal/setup/', views.admin_setup, name='admin_setup'),
    path('admin-portal/student-ranks/', views.admin_student_ranks, name='admin_student_ranks'),
    path('admin-portal/preferences/', views.admin_preferences, name='admin_preferences'),
    path('admin-portal/preferences/<int:student_id>/', views.admin_student_detail, name='admin_student_detail'),
    path('admin-portal/results/', views.admin_results, name='admin_results'),

    # Student
    path('student/preferences/', views.student_preferences, name='student_preferences'),
    path('student/allotment/', views.student_allotment, name='student_allotment'),
]
