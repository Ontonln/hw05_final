from django.shortcuts import render, get_object_or_404, redirect
from .models import Follow, Post, Group, User, Comment
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from .forms import PostForm, CommentForm


FILTER = 10


def paginator(request, posts):
    paginator = Paginator(posts, FILTER)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


def index(request):
    posts = Post.objects.order_by('-pub_date')
    context = {
        'posts': posts,
        'page_obj': paginator(request, posts),
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.order_by('-pub_date')
    context = {
        'group': group,
        'posts': posts,
        'page_obj': paginator(request, posts),
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts_obj = author.posts.order_by('-pub_date')
    posts_count = author.posts.count()
    following = Follow.objects.filter(
        user=request.user.id,
        author=author.id
    ).exists()
    context = {
        'author': author,
        'posts_count': posts_count,
        'page_obj': paginator(request, posts_obj),
        'following': following
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post_det = get_object_or_404(Post, pk=post_id)
    posts_count = Post.objects.filter(author__exact=post_det.author).count()
    post_title = post_det.text[:30]
    comments = Comment.objects.filter(post_id=post_id)
    form = CommentForm(request.POST or None,)
    context = {
        'form': form,
        'comments': comments,
        'post_det': post_det,
        'posts_count': posts_count,
        'post_title': post_title,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if request.method == 'POST':
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('posts:profile', post.author.username)
    return render(request, template, {'form': form})


@login_required
def post_edit(request, post_id):
    template = 'posts/create_post.html'
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        instance=post
    )
    is_edit = post
    if request.user == post.author:
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('posts:post_detail', post_id)
        context = {
            'form': form,
            'is_edit': is_edit,
            'post': post,
        }
        return render(request, template, context)
    return redirect('posts:post_detail', post_id)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    # информация о текущем пользователе доступна в переменной request.user
    post_authors = Post.objects.filter(
        author__following__user=request.user).order_by('-pub_date')
    context = {
        'page_obj': paginator(request, post_authors),
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(author=author, user=request.user)
        return redirect('posts:profile', author.username)
    return redirect('posts:profile', author.username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.get(author=author, user=request.user).delete()
    return redirect('posts:profile', author.username)
