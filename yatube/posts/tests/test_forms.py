from posts.models import Group, Post
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile
from django.conf import settings


User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

    def setUp(self):
        # Неавторизованный
        self.guest_client = Client()
        # Авторизованный
        self.user_auth = User.objects.create_user(username='TestUser')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_auth)
        # Автор
        self.author = Client()
        self.author.force_login(self.user)

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
        form_data = {
            'group': self.group.pk,
            'text': 'Тестовый текст',
            'image': uploaded,
        }
        response = self.author.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse('posts:profile', kwargs={
            'username': self.post.author.username
        }))
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count + 1)
        # Проверяем, что создалась запись с заданными параметрами
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=self.group.pk,
                image='posts/small.gif'
            ).latest('author')
        )

    def test_edit_post(self):
        form_data = {
            'text': 'Test post',
            'group': self.group.pk,
        }
        # Считаем посты
        # До редактирования
        posts_count_edit = Post.objects.count()
        form_data = {
            'text': 'Текст отредактированного поста',
            'group': self.group.pk,
        }
        response = self.author.post(
            reverse('posts:post_edit', kwargs={
                'post_id': self.post.pk
            }),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse('posts:post_detail', kwargs={
            'post_id': self.post.pk
        }))
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count_edit)
        # Проверяем, что запись отредактирована
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=self.group.pk,
            ).exists()
        )
