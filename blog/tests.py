from django.test import TestCase, Client
from bs4 import BeautifulSoup
from .models import Post, Category, Tag, Comment
from django.utils import timezone
from django.contrib.auth.models import User

def create_post(title, content, author, category=None):
    blog_post = Post.objects.create(
        title=title,
        content=content,
        created=timezone.now(),
        author=author,
        category=category,
    )

    return blog_post

def create_category(name='life', description=''):
    category, is_created = Category.objects.get_or_create(
        name=name,
        description=description
    )

    category.slug = category.name.replace(' ', '-').replace('/', '')
    category.save()

    return category


def create_tag(name='some_tag'):
    tag, is_created = Tag.objects.get_or_create(
        name=name
    )
    tag.slug = tag.name.replace(' ', '-').replace('/', '')
    tag.save()

    return tag


def create_comment(post, text='a comment', author=None):
    if author is None:
        author, is_created = User.objects.get_or_create(
            username='guest',
            password='guestpassword'
        )

    comment = Comment.objects.create(
        post=post,
        text=text,
        author=author
    )

    return comment

class TestModel(TestCase):
    def test_comment(self):
        post_000 = create_post(
            title='The first post',
            content='Hello World. We are the world.',
            author=self.author_000,
        )

        self.assertEqual(Comment.objects.count(), 0)

        comment_000 = create_comment(
            post_000
        )

        comment_001 = create_comment(
            post=post_000,
            text='second comment'
        )

        self.assertEqual(Comment.objects.count(), 2)
        self.assertEqual(post_000.comment_set.count(), 2)

class TestView(TestCase):
    def test_post_detail(self):
        category_politics = create_category(name='정치/사회')

        post_000 = create_post(
            title='The first post',
            content='Hello World. We are the world.',
            author=self.author_000,
            category=category_politics
        )

        comment_000 = create_comment(post_000, text='a test comment', author=self.user_obama)
        comment_001 = create_comment(post_000, text='a test comment', author=self.author_000)

        tag_america = create_tag(name='america')
        post_000.tags.add(tag_america)
        post_000.save()

        post_001 = create_post(
            title='The second post',
            content='Second Second Second',
            author=self.author_000,
        )

        self.assertGreater(Post.objects.count(), 0)
        post_000_url = post_000.get_absolute_url()
        self.assertEqual(post_000_url, '/blog/{}/'.format(post_000.pk))

        response = self.client.get(post_000_url)
        self.assertEqual(response.status_code, 200)

        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.title

        self.assertEqual(title.text, '{} - Blog'.format(post_000.title))

        self.check_navbar(soup)

        body = soup.body

        main_div = body.find('div', id='main-div')
        self.assertIn(post_000.title, main_div.text)
        self.assertIn(post_000.author.username, main_div.text)

        self.assertIn(post_000.content, main_div.text)

        self.check_right_side(soup)

        # Comment
        comments_div = main_div.find('div', id='comment-list')
        self.assertIn(comment_000.author.username, comments_div.text)
        self.assertIn(comment_000.text, comments_div.text)

        # Tag
        self.assertIn('#america', main_div.text)

        self.assertIn(category_politics.name, main_div.text)  # category가 main_div에 있다.
        self.assertNotIn('EDIT', main_div.text)  # EDIT 버튼이 로그인하지 않은 경우 보이지 않는다.

        login_success = self.client.login(username='smith', password='nopassword')  # login을 한 경우에는
        self.assertTrue(login_success)
        response = self.client.get(post_000_url)
        self.assertEqual(response.status_code, 200)

        soup = BeautifulSoup(response.content, 'html.parser')
        main_div = soup.find('div', id='main-div')
        self.assertEqual(post_000.author, self.author_000)  # post.author와 login 한 사용자가 동일하면
        self.assertIn('EDIT', main_div.text)  # EDIT 버튼이 있다.

        # 다른 사람인 경우에는 없다.
        login_success = self.client.login(username='obama', password='nopassword')  # login을 한 경우에는
        self.assertTrue(login_success)
        response = self.client.get(post_000_url)
        self.assertEqual(response.status_code, 200)

        soup = BeautifulSoup(response.content, 'html.parser')
        main_div = soup.find('div', id='main-div')
        self.assertEqual(post_000.author, self.author_000)  # post.author와 login 한 사용자가 동일하면
        self.assertNotIn('EDIT', main_div.text)  # EDIT 버튼이 있다.

        comments_div = main_div.find('div', id='comment-list')
        comment_000_div = comments_div.find('div', id='comment-id-{}'.format(comment_000.pk))
        self.assertIn('edit', comment_000_div.text)
        self.assertIn('delete', comment_000_div.text)

        comment_001_div = comments_div.find('div', id='comment-id-{}'.format(comment_001.pk))
        self.assertNotIn('edit', comment_001_div.text)
        self.assertNotIn('delete', comment_001_div.text)


    def test_new_comment(self):
        post_000 = create_post(
            title='The first post',
            content='Hello World. We are the world.',
            author=self.author_000,
        )

        login_success = self.client.login(username='smith', password='nopassword')
        self.assertTrue(login_success)

        response = self.client.post(
            post_000.get_absolute_url() + 'new_comment/',
            {'text': 'A test comment for the first post'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        soup = BeautifulSoup(response.content, 'html.parser')
        main_div = soup.find('div', id='main-div')
        self.assertIn(post_000.title, main_div.text)
        self.assertIn('A test comment', main_div.text)

    def test_delete_comment(self):
        post_000 = create_post(
            title='The first post',
            content='Hello World. We are the world.',
            author=self.author_000,
        )

        comment_000 = create_comment(post_000, text='a test comment', author=self.user_obama)
        comment_001 = create_comment(post_000, text='a test comment', author=self.author_000)

        self.assertEqual(Comment.objects.count(), 2)
        self.assertEqual(post_000.comment_set.count(), 2)

        login_success = self.client.login(username='smith', password='nopassword')
        self.assertTrue(login_success)

        # login을 다른 사람으로 했을 때,
        with self.assertRaises(PermissionError):
            response = self.client.get('/blog/delete_comment/{}/'.format(comment_000.pk), follow=True)
            self.assertEqual(Comment.objects.count(), 2)
            self.assertEqual(post_000.comment_set.count(), 2)

        login_success = self.client.login(username='obama', password='nopassword')
        response = self.client.get('/blog/delete_comment/{}/'.format(comment_000.pk), follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(post_000.comment_set.count(), 1)

        soup = BeautifulSoup(response.content, 'html.parser')
        main_div = soup.find('div', id='main-div')

        self.assertNotIn('obama', main_div.text)

    def test_edit_comment(self):
        post_000 = create_post(
            title='The first post',
            content='Hello World. We are the world.',
            author=self.author_000,
        )

        comment_000 = create_comment(post_000, text='I am president of the US', author=self.user_obama)
        comment_001 = create_comment(post_000, text='a test comment', author=self.author_000)

        # without login
        with self.assertRaises(PermissionError):
            response = self.client.get('/blog/edit_comment/{}/'.format(comment_000.pk))

        # login as smith
        login_success = self.client.login(username='smith', password='nopassword')
        self.assertTrue(login_success)
        with self.assertRaises(PermissionError):
            response = self.client.get('/blog/edit_comment/{}/'.format(comment_000.pk))

        # login as author of the comment. (Obama)
        login_success = self.client.login(username='obama', password='nopassword')
        self.assertTrue(login_success)
        response = self.client.get('/blog/edit_comment/{}/'.format(comment_000.pk))
        self.assertEqual(response.status_code, 200)

        soup = BeautifulSoup(response.content, 'html.parser')
        self.assertIn('Edit Comment: ', soup.body.h3)

        response = self.client.post(
            '/blog/edit_comment/{}/'.format(comment_000.pk),
            {'text': 'I was president of the US'},
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')
        self.assertNotIn('I am president of the US', soup.body.text)
        self.assertIn('I was president of the US', soup.body.text)

    def test_search(self):
        post_000 = create_post(
            title='Stay Fool, Stay Hungry',
            content='Amazing Apple story',
            author=self.author_000
        )

        post_001 = create_post(
            title='Trump Said',
            content='Make America Great Again',
            author=self.author_000
        )

        response = self.client.get('/blog/search/Stay Fool/')
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')
        self.assertIn(post_000.title, soup.body.text)
        self.assertNotIn(post_001.title, soup.body.text)

        response = self.client.get('/blog/search/Make America/')
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')
        self.assertIn(post_001.title, soup.body.text)
        self.assertNotIn(post_000.title, soup.body.text)




