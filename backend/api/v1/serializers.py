from django.contrib.auth import get_user_model
from django.db import transaction
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.exceptions import NotAuthenticated

from users.models import Follow
from recipes.models import (Favorite, Ingredient,
                            IngredientInRecipe, Recipe,
                            ShoppingCart, Tag)


User = get_user_model()


class FoodgramUserSerializer(serializers.ModelSerializer):
    """Сериалайзер для отображения пользователя."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and Follow.objects.filter(
                user=request.user, author=obj
            ).exists()
        )

    def to_representation(self, instance):
        if instance.is_anonymous:
            raise NotAuthenticated('Учетные данные не были предоставлены.')
        return super().to_representation(instance)


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватарки пользователя."""
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):
    """Сериалайзер для тегов."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug',)


class IngredientSerializer(serializers.ModelSerializer):
    """Сериалайзер для ингридиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit',)


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериалайзер для отображения кол-ва ингредиента в рецепте."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeShortSerializer(serializers.ModelSerializer):
    """Для отображения рецептов в подписках."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Отображение полной информации о рецепте."""

    tags = TagSerializer(many=True, read_only=True)
    author = FoodgramUserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        many=True, source='recipe_ingredients', read_only=True
    )
    image = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and Favorite.objects.filter(
                user=request.user, recipe=obj
            ).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and ShoppingCart.objects.filter(
                user=request.user, recipe=obj
            ).exists()
        )


class IngredientWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для игредиентов при записи рецепта.."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount')


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    ingredients = IngredientWriteSerializer(many=True)
    image = Base64ImageField(
        required=True,
        allow_null=False,
        allow_empty_file=False
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'tags', 'image',
            'name', 'text', 'cooking_time'
        )

    def validate(self, data):
        tags = self.initial_data.get('tags')
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Необходимо выбрать тег.'}
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                {'tags': 'Теги не должны повторяться.'}
            )
        ingredients = data.get('ingredients')
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Необходим минимум 1 ингредиент.'}
            )
        ingredient_objects = [item['ingredient'] for item in ingredients]
        if len(ingredient_objects) != len(set(ingredient_objects)):
            raise serializers.ValidationError(
                {'ingredients': 'Ингредиенты не должны повторяться.'}
            )
        if 'image' in data and not data['image']:
            raise serializers.ValidationError(
                {'image': 'Поле изображения не может быть пустым.'}
            )
        if self.context.get(
            'request'
        ).method == 'POST' and 'image' not in data:
            raise serializers.ValidationError(
                {'image': 'Изображение обязательно.'}
            )
        return data

    def valodate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                'Поле картинки не может быть пустым.'
            )
        return value

    @staticmethod
    def create_ingredients_amount(ingredients, recipe):
        IngredientInRecipe.objects.bulk_create([
            IngredientInRecipe(
                recipe=recipe,
                ingredient=ingredient['ingredient'],
                amount=ingredient['amount']
            )
            for ingredient in ingredients
        ])

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')

        recipe = Recipe.objects.create(author=user, **validated_data)
        recipe.tags.set(tags)
        self.create_ingredients_amount(ingredients, recipe)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('ingredients', None)

        instance = super().update(instance, validated_data)
        instance.tags.set(tags)
        instance.recipe_ingredients.all().delete()
        self.create_ingredients_amount(ingredients, instance)

        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance, context=self.context
        ).data


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления в избранное."""

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def validate(self, data):
        if Favorite.objects.filter(
            user=data['user'], recipe=data['recipe']
        ).exists():
            raise serializers.ValidationError('Рецепт уже в избранном.')
        return data

    def to_representation(self, instance):
        return RecipeShortSerializer(
            instance.recipe, context=self.context
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления в список покупок."""

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate(self, data):
        if ShoppingCart.objects.filter(
            user=data['user'], recipe=data['recipe']
        ).exists():
            raise serializers.ValidationError('Рецепт уже в списке покупок.')
        return data

    def to_representation(self, instance):
        return RecipeShortSerializer(
            instance.recipe, context=self.context
        ).data


class SubscriptionSerializer(FoodgramUserSerializer):
    """Сериализатор отображения авторов, на которых подписан пользователь."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(FoodgramUserSerializer.Meta):
        fields = FoodgramUserSerializer.Meta.fields + (
            'recipes', 'recipes_count'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and Follow.objects.filter(
                user=request.user, author=getattr(obj, 'author', obj)
            ).exists()
        )

    def get_recipes_count(self, obj):
        author = getattr(obj, 'author', obj)
        return author.recipes.count()

    def get_recipes(self, obj):
        short_serializer = globals()['RecipeShortSerializer']
        request = self.context.get('request')
        author = getattr(obj, 'author', obj)
        queryset = author.recipes.all()
        if request is not None:
            limit = (
                request.query_params.get('recipes_limit')
                or getattr(request, '_request', request).GET.get('recipes_limit')
            )
            if limit and str(limit).isdigit() and int(limit) > 0:
                queryset = queryset[:int(limit)]
        serializer = short_serializer(queryset, many=True, context=self.context)
        return serializer.data


class SubscribeSerializer(serializers.ModelSerializer):
    """Сериалайзер для создания подписокю"""

    class Meta:
        model = Follow
        fields = ('user', 'author')

    def validate(self, data):
        user = data['user']
        author = data['author']
        if user == author:
            raise serializers.ValidationError(
                'Нельзя подписать ся на самого себя.'
            )
        if Follow.objects.filter(
            user=user, author=author
        ).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого автора.'
            )
        return data

    def to_representation(self, instance):
        return SubscriptionSerializer(
            instance.author, context=self.context
        ).data
