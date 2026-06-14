from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from recipes.models import Recipe, Tag

User = get_user_model()


class FoodgramAPITestCase(TestCase):
    def setUp(self):
        self.guest_client = Client()

        self.user = User.objects.create_user(
            username='test_chef',
            email='chef@foodgram.com',
            password='Password123'
        )

        self.tag = Tag.objects.create(
            name='Завтрак',
            slug='breakfast',
        )

        self.recipe = Recipe.objects.create(
            author=self.user,
            name='Тестовая яичница',
            text='Просто пожарьте яйца',
            cooking_time=5
        )
        self.recipe.tags.add(self.tag)

    def test_recipes_list_exists(self):
        """Проверка доступности списка рецептов для любого гостя."""
        response = self.guest_client.get('/api/recipes/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_tags_list_exists(self):
        """Проверка доступности списка тегов для гостя."""
        response = self.guest_client.get('/api/tags/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_anonymous_cannot_create_recipe(self):
        """Проверка, что анонимный юзер получает отказ при создании рецепта."""
        data = {
            'ingredients': [{'id': 1, 'amount': 10}],
            'tags': [self.tag.id],
            'name': 'Запрещенный рецепт',
            'text': 'Аноним не должен это создать',
            'cooking_time': 10
        }
        response = self.guest_client.post(
            '/api/recipes/',
            data=data,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
