from django.contrib.auth.models import AbstractUser
from django.db import models

NAME_LEN = 150


class User(AbstractUser):
    """Create users."""

    first_name = models.CharField(
        verbose_name='Имя',
        max_length=NAME_LEN
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=NAME_LEN
    )
    email = models.EmailField(
        verbose_name='Адрес электронной почты',
        unique=True
    )
    avatar = models.ImageField(
        verbose_name='Аватар',
        upload_to='users/avatars/',
        blank=True,
        null=True
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('last_name', 'first_name')

    def __str__(self):
        return self.username



class Follow(models.Model):
    """Подписки."""

    user = models.ForeignKey(
        User,
        related_name='follower',
        on_delete=models.CASCADE,
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        related_name='following',
        on_delete=models.CASCADE,
        verbose_name='Автор'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ('author__username', 'user__username')
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_follower'
            ),
            models.CheckConstraint(
                condition=~models.Q(user=models.F('author')),
                name='user_cannot_follow_oneself'
            )
        ]

    def __str__(self):
        return f'{self.user.username} подписан на {self.author.username}'
