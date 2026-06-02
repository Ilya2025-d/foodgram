import csv
import os
from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    """Команда для ипорта данных в Ingredient."""

    help = 'Загрузка ингридиентов из CSV в базу.'

    def handle(self, *args, **options):
        file_path = os.path.join(
            settings.BASE_DIR, '..', 'data', 'ingredients.csv'
        )
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(
                f'Файл не найден по пути: {file_path}'
            ))
            return

        self.stdout.write('Начало импорта ингредиентов...')

        ingredients_to_create = []

        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                name = row[0]
                measurement_unit = row[1]

                ingredients_to_create.append(
                    Ingredient(name=name, measurement_unit=measurement_unit)
                )

        Ingredient.objects.bulk_create(
            ingredients_to_create, ignore_conflicts=True
        )

        self.stdout.write(self.style.SUCCESS(
            f'Успешно загружено ингредиентов: {len(ingredients_to_create)}'
        ))
