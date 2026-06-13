from django_filters import rest_framework
from django.contrib.auth import get_user_model

from recipes.models import Ingredient, Recipe, Tag


User = get_user_model()


class IngredientFilter(rest_framework.FilterSet):
    """Фильтр для поиска ингредиента по названию."""

    name = rest_framework.CharFilter(
        field_name='name',
        lookup_expr='istartswith'
    )

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(rest_framework.FilterSet):
    """Фильтрация рецептов."""

    tags = rest_framework.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )
    author = rest_framework.ModelChoiceFilter(
        queryset=User.objects.all()
    )
    is_favorited = rest_framework.NumberFilter(
        method='filter_is_favorited'
    )
    is_in_shopping_cart = rest_framework.NumberFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = (
            'tags', 'author', 'is_favorited', 'is_in_shopping_cart'
        )

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if user.is_authenticated and value == 1:
            return queryset.filter(favorited_by__user=user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if user.is_authenticated and value == 1:
            return queryset.filter(in_shopping_cart__user=user)
        return queryset
