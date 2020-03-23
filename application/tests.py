from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase
from django.test import Client
from django.urls import reverse
from .views import *

class SimpleTest(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.credentials = {
            'username': 'testuser',
            'password': 'secret'}
        User.objects.create_user(**self.credentials)

    def test_login(self):
        c = Client()
        # send login data
        url = reverse('login')
        response = c.post(url, self.credentials, follow=True)
        # should be logged in now
        self.assertTrue(response.context['user'].is_active)

    def test_signup(self):
        # Create an instance of a GET request.



        c = Client()
        url = reverse('signup')
        response = c.post(url, {'username': 'john', 'password1': 'Boredman1!','password2': 'Boredman1!', 'email': 'johnsmith@test.com', 'first_name':'john', 'last_name': 'smith'})
        response.status_code
        self.assertEqual(response.status_code, 200)

    def test_page_blocked(self):
        url = reverse('simulator')
        request = self.factory.get(url)
        request.user = AnonymousUser()
        response = fmSimulator(request)
        response.client = Client()
        expected_url = reverse('please_login')
        self.assertRedirects(response,expected_url)