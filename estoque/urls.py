from django.urls import path

from . import views

app_name = 'estoque'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('gerenciar/', views.gerenciar_estoque, name='gerenciar'),
    path('consultar/', views.consultar_estoque, name='consultar'),
]
