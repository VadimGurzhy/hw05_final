from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
import shutil
import tempfile
from posts.models import Group, Post, Comment
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем авторизованный клиент (автор поста)
        self.authorized_author_client = Client()
        self.authorized_author_client.force_login(self.user)

    def test_create_post(self):
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        form_post = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': uploaded
        }

        response = self.authorized_author_client.post(
            reverse('posts:post_create'),
            data=form_post,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый текст',
                group=PostFormTests.group.id,
                author=PostFormTests.post.author,
                image=PostFormTests.post.image
            ).exists()
        )

    def test_edit_post(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        form_post = {
            'text': 'Измененный текст',
            'group': self.group,
            'image': uploaded
        }
        response = self.authorized_author_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_post,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context['post'].text, form_post['text'])
        self.assertTrue(
            Post.objects.filter(
                group=PostFormTests.group.id,
                author=PostFormTests.post.author
            ).exists()
        )

    def test_create_comment(self):
        """Валидная форма создает запись в Comment."""
        comment_count = Comment.objects.count()
        form_post = {
            'text': 'Новый комментарий'
        }
        response = self.authorized_author_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': PostFormTests.post.pk}
            ),
            data=form_post,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            kwargs={'post_id': PostFormTests.post.pk}
        ))
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text='Новый комментарий',
                post=PostFormTests.post.id,
                author=PostFormTests.post.author,
            ).exists()
        )
