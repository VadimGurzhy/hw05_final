from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from ..models import Group, Post
from http import HTTPStatus

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser')
        cls.user1 = User.objects.create_user(username='anotheruser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='testslug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя автора
        self.authorized_client.force_login(self.user)
        # Создаем третий клиент
        self.authorized_client1 = Client()
        self.authorized_client1.force_login(self.user1)

    def test_urls_exists_statuses(self):
        """Тестирование общедоступных страниц."""
        response_url_status = {
            '': HTTPStatus.OK,
            '/group/testslug/': HTTPStatus.OK,
            '/profile/testuser/': HTTPStatus.OK,
            '/posts/1/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND
        }

        for url, status_code in response_url_status.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, status_code)

    def test_post_create_urls(self):
        """Страница /create/ доступна только авторизованному пользователю."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_posts_urls(self):
        """Страница /posts/<post_id>/edit/ доступна только авторизованному
        пользователю."""
        response = self.authorized_client.get(
            '/posts/1/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_urls_redirect_anonymous(self):
        response = self.guest_client.get('/create/')
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_post_posts_urls_redirect_anonymous(self):
        response = self.guest_client.get('/posts/1/edit/')
        self.assertRedirects(response, '/auth/login/?next=/posts/1/edit/')

    def test_post_posts_urls_redirect_non_author(self):
        response = self.authorized_client1.get('/posts/1/edit/')
        self.assertRedirects(response, '/posts/1/')
