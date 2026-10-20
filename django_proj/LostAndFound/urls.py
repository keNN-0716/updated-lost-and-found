from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),

    path('login_redirect/', views.login_redirect_view, name='login_redirect'),

    path('lost_and_found/', views.lost_and_found, name='lost_and_found'),
    path('user_home_page/', views.user_home_page, name='user_home_page'),

    path('lost_items/', views.lost_items, name='lost_items'),
    path('found_items/', views.found_items, name='found_items'),
    path('search/', views.search_results, name='search_results'),
    path('api/search/', views.search_api, name='search_api'),   # ← NEW

    path('claim_request/<str:item_type>/<int:item_id>/', views.submit_claim_request, name='submit_claim_request'),
    path('resolve/<str:item_type>/<int:item_id>/', views.resolve_item, name='resolve_item'),
    
    path('management/requests/', views.management_requests, name='management_requests'),
    path('management/requests/process/<int:req_id>/<str:action>/', views.process_claim_request, name='process_claim_request'),
    
    path('claim/qr/<int:req_id>/', views.claim_qr_code, name='claim_qr_code'),
    path('verify/<int:req_id>/', views.verify_claim, name='verify_claim'),
]