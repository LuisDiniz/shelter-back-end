from django.urls import path
from . import views

urlpatterns = [
    path('', views.AnimalList.as_view(), name='animais'),

    path('api/animals', views.animal_list_api, name='animal_list_create_no_slash'),
    path('api/animals/', views.animal_list_api, name='animal_list_create'),
    path('api/animals/<int:animal_id>/', views.animal_detail_api, name='animal_detail'),

    path('animal/<int:animal_id>', views.AnimalDetails.as_view(), name='get_animal_details'),
    path('animal', views.AnimalDetails.as_view(), name='save_animal_details'),

    path('animal-image/<int:animal_id>', views.AnimalImagens.as_view(), name='save_animal_image'),
]
