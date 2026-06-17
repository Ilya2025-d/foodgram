from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import permissions, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from api.v1.filters import IngredientFilter, RecipeFilter
from api.v1.permissions import IsAuthorOrAdminOrReadOnly
from api.v1.serializers import (AvatarSerializer, FavoriteSerializer,
                                IngredientSerializer, RecipeReadSerializer,
                                RecipeWriteSerializer, ShoppingCartSerializer,
                                SubscribeSerializer, SubscriptionSerializer,
                                TagSerializer)
from api.v1.pagination import LimitPageNumberPagination
from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, Tag)
from users.models import Follow


User = get_user_model()


@api_view(['GET'])
def redirect_to_recipe(request, short_code):
    """Перенаправляет короткую ссылку на полную страницу рецепта."""
    recipe = get_object_or_404(Recipe, short_link_code=short_code)
    return redirect(f'/recipes/{recipe.id}/')


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Представление тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Представление ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """Представление для рецептов."""

    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = LimitPageNumberPagination

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        short_link = request.build_absolute_uri(
            f'/s/{recipe.short_link_code}'
        )
        return Response(
            {'short-link': short_link}, status=HTTPStatus.OK
        )

    @action(
        detail=True, methods=['post'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        serializer = FavoriteSerializer(
            data={'user': request.user.id, 'recipe': recipe.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data, status=HTTPStatus.CREATED
        )

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        deleted_count, _ = Favorite.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted_count:
            return Response(
                {'errors': 'Рецепта не было в избранном.'},
                status=HTTPStatus.BAD_REQUEST
            )
        return Response(status=HTTPStatus.NO_CONTENT)

    @action(
        detail=True, methods=['post'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        serializer = ShoppingCartSerializer(
            data={'user': request.user.id, 'recipe': recipe.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data, status=HTTPStatus.CREATED
        )

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        deleted_count, _ = ShoppingCart.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted_count:
            return Response(
                {'errors': 'Рецепта не было в списке покупок.'},
                status=HTTPStatus.BAD_REQUEST
            )
        return Response(status=HTTPStatus.NO_CONTENT)

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        user = request.user

        if not user.shopping_cart.exists():
            return Response(
                {'errors': 'Ваш список покупок пуст.'},
                status=HTTPStatus.BAD_REQUEST
            )
        ingredients = IngredientInRecipe.objects.filter(
            recipe__in_shopping_cart__user=user
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')

        wish_list = ['Ваш список покупок:\n\n']
        for item in ingredients:
            wish_list.append(
                f"- {item['ingredient__name']} "
                f"({item['ingredient__measurement_unit']}) "
                f"— {item['total_amount']}\n"
            )
        content = ''.join(wish_list)
        response = HttpResponse(
            content, content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_cart.txt"'
        )
        return response


class FoodgramUserViewSet(UserViewSet):
    """Представление для пользователей и подписокю"""

    pagination_class = LimitPageNumberPagination

    @action(
        detail=False, methods=['get'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=HTTPStatus.OK)

    @action(
        detail=False, methods=['get'])
    def subscriptions(self, request):
        user = request.user
        authors = User.objects.filter(following__user=user)
        page = self.paginate_queryset(authors)
        serializer = SubscriptionSerializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True, methods=['post'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def subscribe(self, request, id=None):
        """Подписка на автора."""
        author = get_object_or_404(User, id=id)
        serializer = SubscribeSerializer(
            data={'user': request.user.id, 'author': author.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data, status=HTTPStatus.CREATED
        )

    @subscribe.mapping.delete
    def unsubscribe(self, request, id=None):
        author = get_object_or_404(User, id=id)
        deleted_count, _ = Follow.objects.filter(
            user=request.user, author=author
        ).delete()
        if not deleted_count:
            return Response(
                {'errors': 'Вы не были подписаны на этого автора.'},
                status=HTTPStatus.BAD_REQUEST
            )
        return Response(status=HTTPStatus.NO_CONTENT)

    @action(
        detail=False, methods=['put'],
        url_path='me/avatar',
        permission_classes=[permissions.IsAuthenticated]
    )
    def avatar(self, request):
        """Обновление или добавление аватара пользователя."""
        user = request.user
        serializer = AvatarSerializer(
            user, data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=HTTPStatus.OK)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        """Удаление аватара пользователя."""
        user = request.user
        if user.avatar:
            user.avatar.delete(save=True)
        return Response(status=HTTPStatus.NO_CONTENT)
