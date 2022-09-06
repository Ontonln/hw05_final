from django import forms
from .models import Post, Comment
from django.utils.translation import gettext_lazy as _


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('group', 'text', 'image')
        labels = {
            'group': _('Группа'),
            'text': _('Текст поста'),
        }
        help_texts = {
            'group': _('Группа, к которой будет относиться пост'),
            'text': _('Текст нового поста'),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
