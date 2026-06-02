from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db.models import Sum
from djoser.views import UserViewSet
from http import HTTPStatus

from users.models import User, Follow
from recipes.models import (IngredientInRecipe, Tag, Ingredient,
                            Recipe, Favorite, ShoppingCart)
from .serializers import (RecipeShortSerializer, TagSerializer,
                          IngredientSerializer,
                          RecipeReadSerializer,
                          RecipeWriteSerializer,
                          SubscriptionSerializer,
                          AvatarSerializer)
from .permissions import IsAuthorOrReadOnly
from .pagination import CustomPagination


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

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        name_param = self.request.query_params.get('name')
        if name_param:
            queryset = queryset.filter(name__istartswith=name_param)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    """Представление для рецептов."""

    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnly,)
    pagination_class = CustomPagination
    lookup_value_converter = 'int'

    def get_permissions(self):
        if self.action in (
            'download_shopping_cart', 'favorite', 'shopping_cart'
        ):
            return (permissions.IsAuthenticated(),)
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        else:
            return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        queryset = Recipe.objects.all()
        author_param = self.request.query_params.get('author')
        if author_param:
            queryset = queryset.filter(author_id=author_param)
        tags_param = self.request.query_params.get('tags')
        tags_param = self.request.query_params.getlist('tags')
        if tags_param:
            tags_queryset = Tag.objects.filter(slug__in=tags_param)
            queryset = queryset.filter(tags__in=tags_queryset).distinct()
        user = self.request.user
        if user.is_authenticated:
            if self.request.query_params.get('is_favorited') == '1':
                queryset = queryset.filter(favorited_by__user=user)
            if self.request.query_params.get('is_in_shopping_cart') == '1':
                queryset = queryset.filter(in_shopping_cart__user=user)
        return queryset

    @action(detail=True, methods=['get'], url_path='get-link')  # Кнопка
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        short_link = f'{request.build_absolute_uri("/")}s/{recipe.id}'
        return Response({'short-link': short_link}, status=HTTPStatus.OK)

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == 'POST':
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт уже в избраном.'},
                    status=HTTPStatus.BAD_REQUEST
                )
            Favorite.objects.create(user=user, recipe=recipe)
            serializer = RecipeShortSerializer(recipe)
            return Response(serializer.data, status=HTTPStatus.CREATED)

        if request.method == 'DELETE':
            favorite_record = Favorite.objects.filter(user=user, recipe=recipe)
            if favorite_record.exists():
                favorite_record.delete()
                return Response(status=HTTPStatus.NO_CONTENT)
            return Response(
                {'errors': 'Рецепта не было в избранном.'},
                status=HTTPStatus.BAD_REQUEST
            )

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт уже в списке покупок.'},
                    status=HTTPStatus.BAD_REQUEST
                )
            ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = RecipeShortSerializer(recipe)
            return Response(serializer.data, status=HTTPStatus.CREATED)

        if request.method == 'DELETE':
            cart_record = ShoppingCart.objects.filter(user=user, recipe=recipe)
            if cart_record.exists():
                cart_record.delete()
                return Response(status=HTTPStatus.NO_CONTENT)
            return Response(
                {'errors': 'Рецепта не было в списке покупок.'},
                status=HTTPStatus.BAD_REQUEST
            )

    @action(detail=False, methods=['GET'])
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
            'ingredient__name',
            'ingredient__measurement_unit'
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


class CustomUserViewSet(UserViewSet):
    """Представление для пользователей и подписокю"""

    pagination_class = CustomPagination

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        user = request.user
        authors = User.objects.filter(following__user=user)
        page = self.paginate_queryset(authors)
        if page is not None:
            serializer = SubscriptionSerializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = SubscriptionSerializer(
            authors,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'])
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, id=id)

        if request.method == 'POST':
            if user == author:
                return Response(
                    {'errors': 'Нельзя подпмсаться на самого себя'},
                    status=HTTPStatus.BAD_REQUEST
                )
            if Follow.objects.filter(user=user, author=author).exists():
                return Response(
                    {'errors': 'Вы уже подпмсаны на этого автора'},
                    status=HTTPStatus.BAD_REQUEST
                )
            Follow.objects.create(user=user, author=author)
            serializer = SubscriptionSerializer(
                author, context={'request': request}
            )
            return Response(serializer.data, status=HTTPStatus.CREATED)

        if request.method == 'DELETE':
            subscription = Follow.objects.filter(user=user, author=author)
            if subscription.exists():
                subscription.delete()
                return Response(status=HTTPStatus.NO_CONTENT)
            return Response(
                {'errors': 'Вы не подписаны на этого автора'},
                status=HTTPStatus.BAD_REQUEST
            )

    @action(
        detail=False,
        methods=['put', 'delete'],
        url_path='me/avatar'
    )
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            serializer = AvatarSerializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=HTTPStatus.OK)

        if request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete(save=True)
            return Response(status=HTTPStatus.NO_CONTENT)

    def get_permissions(self):
        if self.action in ('subscriptions', 'subscribe', 'avatar'):
            return (permissions.IsAuthenticated(),)
        if self.action in ('list', 'retrieve'):
            return (permissions.AllowAny(),)
        return super().get_permissions()
