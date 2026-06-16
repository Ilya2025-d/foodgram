import random
import string

from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

NAME_LEN = 32
SLUG_LEN = 32
INGRED_LEN = 128
MEASU_UNIT_LEN = 64
RECIPE_NAME = 256
LINK_LEN = 10
MIN_COOK_TIME = 1
MAX_COOK_TIME = 32000
MIN_INGREDIENT = 1
MAX_INGREDIENT = 32000


User = get_user_model()


class Tag(models.Model):
    """Таблица тегов."""

    name = models.CharField(
        verbose_name='Тег',
        max_length=NAME_LEN,
        unique=True
    )
    slug = models.SlugField(
        verbose_name='Слаг',
        max_length=SLUG_LEN,
        unique=True
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Таблица ингридиентов."""

    name = models.CharField(
        verbose_name='Ингридиент',
        max_length=INGRED_LEN
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=MEASU_UNIT_LEN
    )

    class Meta:
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'Ингридиенты'
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_name_measurement_unit'
            )
        ]

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Таблица рецептов."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    name = models.CharField(
        verbose_name='Название рецепта',
        max_length=RECIPE_NAME
    )
    image = models.ImageField(
        verbose_name='Изображение рецепта'
    )
    text = models.TextField(
        verbose_name='Описанние рецепта'
    )
    tags = models.ManyToManyField(
        Tag
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientInRecipe',
        verbose_name='Ингредиенты'
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления',
        validators=[
            MinValueValidator(
                MIN_COOK_TIME, message=f'Нельзя меньше {MIN_COOK_TIME}'
            ),
            MaxValueValidator(
                MAX_COOK_TIME, message=f'Нельзя больше {MAX_COOK_TIME}'
            )
        ]
    )
    short_link_code = models.CharField(
        max_length=LINK_LEN,
        unique=True,
        verbose_name='Короткая ссылка'
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('name', '-id')

    def __str__(self):
        return self.name

    def save(self, *args, **options):
        if not self.short_link_code:
            self.short_link_code = self.generate_short_code()
            while Recipe.objects.filter(
                short_link_code=self.short_link_code
            ).exists():
                self.short_link_code = self.generate_short_code()
        super().save(*args, **options)

    def generate_short_code(self, length=6):
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))


class IngredientInRecipe(models.Model):
    """Таблица связей рецептов с ингридиентами."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient_recipes',
        verbose_name='Ингредиент'
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='кол-во ингредиентов',
        validators=[
            MinValueValidator(
                MIN_INGREDIENT, message=f'Нельзя меньше {MIN_INGREDIENT}'
            ),
            MaxValueValidator(
                MAX_INGREDIENT, message=f'Нельзя больше {MAX_INGREDIENT}'
            )
        ]
    )

    class Meta:
        verbose_name = 'Cвязm рецепта с ингридиентом'
        verbose_name_plural = 'Связи рецептов с ингредиентами'
        ordering = ('ingredient__name',)
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]

    def __str__(self):
        return (
            f'{self.ingredient.name} — {self.amount} '
            f'{self.ingredient.measurement_unit}'
        )


class Favorite(models.Model):
    """Избранное."""

    user = models.ForeignKey(
        User,
        related_name='favorites',
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        related_name='favorited_by',
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        ordering = ('user', 'recipe')
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite_recipe'
            )
        ]

    def __str__(self):
        return (
            f'Пользователь {self.user.username} '
            f'добавил в избранное: "{self.recipe.name}"'
        )


class ShoppingCart(models.Model):
    """Список покупок."""

    user = models.ForeignKey(
        User,
        related_name='shopping_cart',
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        related_name='in_shopping_cart',
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'
        ordering = ('user', 'recipe')
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart_recipe'
            )
        ]

    def __str__(self):
        return (
            f'Рецепт {self.recipe.name} '
            f' в списке у {self.user.username}'
        )
