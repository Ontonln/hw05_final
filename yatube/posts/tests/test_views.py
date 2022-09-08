from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Comment, Follow, Group, Post

from ..views import FILTER

User = get_user_model()


class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user2 = User.objects.create_user(username='auth_user_2')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test_slug_2',
            description='Тестовое описание 2',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=cls.uploaded,
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user2,
            text='Тестовый Комментарий'
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
        # Авторизованный юзер
        self.user_follow = Client()
        self.user_follow.force_login(self.user2)

    def test_follow(self):
        """Кнопка подписки не работает"""
        user = self.user2
        author = self.user
        # Подписка создана через запрос от юзера
        self.user_follow.get(reverse('posts:profile_follow', kwargs={
            'username': author.username
        }))
        self.assertTrue(
            Follow.objects.filter(
                user=user,
                author=author,
            ).exists()
        )

    def test_unfollow(self):
        """Кнопка отписки не работает"""
        user = self.user2
        author = self.user
        Follow.objects.create(
            user=user,
            author=author,
        )
        self.user_follow.get(reverse('posts:profile_unfollow', kwargs={
            'username': author.username
        }))
        self.assertFalse(
            Follow.objects.filter(
                user=user,
                author=author,
            ).exists()
        )

    def check_page_obj_at_context(self, response):
        """Эта функция является частью простого контекстного тестирования.
        Она создана для того, что бы не создавать повторяющиеся конструкции"""
        first_object_post = response.context.get("page_obj")[0]
        self.assertEqual(first_object_post.author.username, 'auth')
        self.assertEqual(first_object_post.text, 'Тестовый пост')
        self.assertEqual(first_object_post.group.title, 'Тестовая группа')
        self.assertEqual(first_object_post.image.read(), self.small_gif)

    def test_post_created_at_right_group_and_profile(self):
        """Тестовый пост создан не в той группе и профиле"""
        urls = (reverse('posts:group_list', kwargs={
                        'slug': self.group2.slug
                        }),
                reverse('posts:profile', kwargs={
                        'username': self.user2.username
                        }),
                )
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                page_obj = response.context.get("page_obj")
                self.assertEqual(len(page_obj), 0)

    def test_follow_page(self):
        """Страница подписок отображаются неверно"""
        user = self.user2
        author = self.user
        # Подписка создана через запрос от юзера
        Follow.objects.create(
            user=user,
            author=author
        )
        # Посты в подписках
        post_follow = Post.objects.get(author__following__user=user)
        # Посты авторов на которых подписан
        post_authors = Post.objects.get(author=author)
        # Сравниваю
        self.assertEqual(post_follow.id, post_authors.id)

# Profile
    def test_profile_use_correct_context(self):
        """Тест Profile."""
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.post.author}))
        user_obj = response.context.get("author")
        self.assertEqual(user_obj.id, self.post.author.id)
        self.check_page_obj_at_context(response)

# Детали поста
    def test_post_detail_correct_context(self):
        """Тест Post."""
        response = self.client.get(
            reverse("posts:post_detail", kwargs={"post_id": self.post.pk})
        )
        post_obj = response.context.get("post_det")
        self.assertEqual(post_obj.id, self.post.pk)
        self.assertEqual(post_obj.image.read(), self.small_gif)
        self.assertIn(self.comment, response.context['comments'])

# Glavnaya
    def test_index_correct_context(self):
        """Тест Index."""
        response = self.client.get(reverse("posts:index"))
        self.check_page_obj_at_context(response)

# Тест группы
    def test_group_posts_correct_context(self):
        """Тест Group."""
        response = self.client.get(
            reverse("posts:group_list", kwargs={"slug": self.group.slug})
        )
        group_obj = response.context.get("group")
        self.assertEqual(group_obj, Group.objects.get(id=1))
        self.check_page_obj_at_context(response)

# Context Create And Edit
    def test_create_and_edit_page_show_correct_context(self):
        """Шаблон create и edit сформирован с неправильным контекстом."""
        # Словарь ожидаемых типов полей формы:
        # указываем, объектами какого класса должны быть поля формы
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        reverse_list = [
            reverse('posts:post_create'),
            reverse('posts:post_edit', kwargs={
                'post_id': self.post.pk
            }),
        ]
        for reverse_name in reverse_list:
            with self.subTest(reverse_name=reverse_name):
                response = self.author.get(reverse_name)
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = response.context['form'].fields[value]
                        self.assertIsInstance(form_field, expected)
                        self.assertEqual(len(form_fields), 3)

# Namespace ++++++
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={
                'slug': self.group.slug
            }): 'posts/group_list.html',
            reverse('posts:profile', kwargs={
                'username': self.post.author
            }): 'posts/profile.html',
            reverse('posts:post_detail', kwargs={
                'post_id': self.post.pk
            }): 'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={
                'post_id': self.post.pk
            }): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for address, template in templates_pages_names.items():
            with self.subTest(address=address):
                response = self.author.get(address)
                self.assertTemplateUsed(response, template)

    def test_index_cache(self):
        """Тестирование кеша"""
        # Создаю пост
        test_post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
            group=self.group,
            image=self.uploaded,
        )
        # Запрашиваю главную страницу
        response = self.authorized_client.get(reverse('posts:index'))
        # И сохраняю ее
        cache_responce = response.content
        # Удаляю пост
        test_post.delete()
        # Запрашиваю главную страницу
        response = self.authorized_client.get(reverse('posts:index'))
        # Сравниваю
        self.assertEqual(cache_responce, response.content)
        # Очищаю кеш
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(cache_responce, response.content)


# Paginator ++++++
class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='User1')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = [
            Post(
                author=cls.user,
                group=cls.group,
                text=f'Тестовый пост {i}',
            )
            for i in range(15)
        ]
        Post.objects.bulk_create(cls.post)

    def test_first_page_contains_ten_records(self):
        pages = {
            reverse('posts:index'): 'page_obj',
            reverse('posts:group_list', kwargs={
                'slug': self.group.slug
            }): 'page_obj',
            reverse('posts:profile', kwargs={
                'username': self.user
            }): 'page_obj',
        }
        for address, template in pages.items():
            with self.subTest(address=address):
                response = self.client.get(address)
                self.assertEqual(len(response.context[template]), FILTER)
