from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Group, User, Follow
from .forms import PostForm, CommentForm
from django.contrib.auth.decorators import login_required
from .utils import get_paginator
from django.views.decorators.cache import cache_page
from django.core.paginator import Paginator

PAGINATOR_PAGES = 10


@cache_page(20)
def index(request):
    post_list = Post.objects.all().order_by('-pub_date')
    pagin = get_paginator(post_list, request)
    context = {
        'page_obj': pagin['page_obj'],
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = Post.objects.all().filter(
        group=group).order_by('-pub_date')
    pagin = get_paginator(posts, request)
    context = {
        'page_obj': pagin['page_obj'],
        'group': group,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()  # type: ignore
    count = author.posts.count()  # type: ignore
    pagin = get_paginator(posts, request)
    context = {
        'author': author,
        'count': count,
        'posts': posts,
        'page_obj': pagin['page_obj'],
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    pub_date = post.pub_date
    post_title = post.text[:30]
    author = post.author
    author_posts = author.posts.all().count()
    comments = post.comments.all()
    form = CommentForm()
    context = {
        'post': post,
        'post_title': post_title,
        'author': author,
        'author_posts': author_posts,
        'pub_date': pub_date,
        'comments': comments,
        'form': form,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', request.user)
    form = PostForm()
    context = {
        'form': form,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect(
            'posts:post_detail', post_id
        )
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect(
            'posts:post_detail', post_id
        )
    template = 'posts/create_post.html'
    context = {
        'form': form,
        'is_edit': True,
        'post': post,
    }
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = get_object_or_404(Post, pk=post_id)
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    template = 'posts/follow.html'
    title = 'Публикации интересных авторов'
    posts = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(posts, PAGINATOR_PAGES)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'title': title,
        'page_obj': page_obj,
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:profile', author)


@login_required
def profile_unfollow(request, username):
    user_follower = get_object_or_404(
        Follow,
        user=request.user,
        author__username=username
    )
    user_follower.delete()
    return redirect('posts:profile', username)
