from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
import shutil
import tempfile

from ..models import Group, Post, Follow
from ..forms import PostForm
from django.core.cache import cache

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug_slug',
            description='Тестовое описание',
        )

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B')

        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def post_info(self, post):
        with self.subTest(post=post):
            self.assertEqual(post.text, self.post.text)
            self.assertEqual(post.author, self.post.author)
            self.assertEqual(post.group.id, self.post.group.id)
            self.assertEqual(post.image, self.post.image)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            (
                reverse('posts:group_list', kwargs={'slug': 'slug_slug'})
            ): 'posts/group_list.html',
            (
                reverse(
                    'posts:profile', kwargs={'username': self.user.username})
            ): 'posts/profile.html',
            (
                reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
            ): 'posts/post_detail.html',
            (
                reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.post_info(response.context['page_obj'][0])

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': 'slug_slug'}))
        self.assertEqual(response.context['group'], self.group)
        self.post_info(response.context['page_obj'][0])

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': 'testuser'}))
        self.assertEqual(response.context['author'], self.user)
        self.post_info(response.context['page_obj'][0])

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk}))
        self.post_info(response.context['post'])

    def test_edit_post_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом. """
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.pk}
        ))
        self.assertIsInstance(response.context['form'], PostForm)

    def test_create_post_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get('/create/')
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_correctly(self):
        response_index = self.authorized_client.get(
            reverse('posts:index'))
        response_group = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'slug_slug'}))
        response_profile = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'testuser'}))
        self.assertContains(response_index, self.post.text)
        self.assertContains(response_group, self.post.text)
        self.assertContains(response_profile, self.post.text)

    def test_cache_index_page(self):
        post = Post.objects.create(
            text='Пост для проверки кеша',
            author=self.user
        )
        response = self.authorized_client.get(
            reverse('posts:index')).content
        post.delete()
        response_delete = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertEqual(response, response_delete)
        cache.clear()
        response_cache_clear = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertNotEqual(response, response_cache_clear)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser')
        cls.group1 = Group.objects.create(
            title='Тестовая группа',
            slug='slug_slug',
            description='Тестовое описание',
        )
        text_posts = [Post(
            author=cls.user,
            text='Тестовый пост' + str(i),
            group=cls.group1) for i in range(13)]
        cls.post = Post.objects.bulk_create(text_posts)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_paginator(self):
        first_page = 10
        second_page = 3
        pages_url = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'slug_slug'}),
            reverse('posts:profile', kwargs={'username': 'testuser'}),
        ]
        for pages in pages_url:
            with self.subTest(pages=pages):
                self.assertEqual(len(self.client.get(
                    pages).context.get('page_obj')),
                    first_page)
                self.assertEqual(len(self.client.get(
                    pages + '?page=2').context.get('page_obj')),
                    second_page)


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_autor = User.objects.create(
            username='post_autor',
        )
        cls.post_follower = User.objects.create(
            username='post_follower',
        )
        cls.post = Post.objects.create(
            text='Подпишись',
            author=cls.post_autor,
        )

    def setUp(self):
        cache.clear()
        self.author_client = Client()
        self.author_client.force_login(self.post_follower)
        self.follower_client = Client()
        self.follower_client.force_login(self.post_autor)

    def test_follow_on_user(self):
        count_follow = Follow.objects.count()
        self.follower_client.post(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.post_follower}))
        follow = Follow.objects.all().latest('id')
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.assertEqual(follow.author_id, self.post_follower.id)
        self.assertEqual(follow.user_id, self.post_autor.id)

    def test_unfollow_on_user(self):
        Follow.objects.create(
            user=self.post_autor,
            author=self.post_follower)
        count_follow = Follow.objects.count()
        self.follower_client.post(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.post_follower}))
        self.assertEqual(Follow.objects.count(), count_follow - 1)

    def test_follow_on_authors(self):
        post = Post.objects.create(
            author=self.post_autor,
            text="Подпишись на меня")
        Follow.objects.create(
            user=self.post_follower,
            author=self.post_autor)
        response = self.author_client.get(
            reverse('posts:follow_index'))
        self.assertIn(post, response.context['page_obj'].object_list)

    def test_notfollow_on_authors(self):
        post = Post.objects.create(
            author=self.post_autor,
            text="Подпишись на меня")
        response = self.author_client.get(
            reverse('posts:follow_index'))
        self.assertNotIn(post, response.context['page_obj'].object_list)
