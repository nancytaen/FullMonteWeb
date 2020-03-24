from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase
from django.test import Client
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from .views import *

class SimpleTest(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.credentials = {
            'username': 'testuser',
            'password': 'secret'}
        User.objects.create_user(**self.credentials)
        self.user = User.objects.create_user(
            username='testuser2', first_name="test", 
            last_name="user", email='testuser2@test.com', password='Top_secret')

    #test if log in workds
    def test_login(self):
        c = Client()
        # send login data
        url = reverse('login')
        response = c.post(url, self.credentials, follow=True)
        # should be logged in now
        self.assertTrue(response.context['user'].is_active)

    #test if signup works
    def test_signup(self):
        c = Client()
        url = reverse('signup')
        response = c.post(url, {'username': 'john', 'password1': 'Boredman1!','password2': 'Boredman1!',
            'email': 'johnsmith@test.com', 'first_name':'john', 'last_name': 'smith'})
        self.assertEqual(response.status_code, 200)

    #test if user cannot access blocked pages when not logged in
    def test_page_blocked(self):
        url = reverse('simulator')
        request = self.factory.get(url)
        #anonymous user because not logged in
        request.user = AnonymousUser()
        response = fmSimulator(request)
        response.client = Client()
        expected_url = reverse('please_login')
        #check that it redirects to please log in page
        self.assertRedirects(response,expected_url)

    #test if change password works
    def test_change_password(self):
        c = Client()
        user = self.user
        url = reverse('change_password')
        request = self.factory.post(url,{'old_password': 'Top_secret',
            'new_password1': 'Testchange1','new_password2': 'Testchange1'})
        request.user = self.user
        #set a session to request
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()
        #add messages to request
        middleware = MessageMiddleware()
        middleware.process_request(request)
        request.session.save()
        response = change_password(request)
        #check that password = new password
        self.assertEquals(self.user.check_password("Testchange1"), True)

    def test_reset_password(self):
        c = Client()
       

        # Post request with email
        response = c.post(reverse('password_reset'),{'email':'testuser2@test.com'})
        # Check that an email has been sent
        self.assertEqual(len(mail.outbox), 1)
        #check subject line
        self.assertEqual(mail.outbox[0].subject, 'Password Reset - FullMonte')

        # get token and user ID
        token = response.context[0]['token']
        uid = response.context[0]['uid']
        url = reverse('password_reset_confirm', args=(uid,token))
        response = c.get(url, follow=True)
        #url of where to post new password
        url2=reverse('password_reset_confirm', args=(uid,'set-password'))

        #post to the same url with our new password
        response = c.post(url2, {'new_password1':'Testpassword1','new_password2':'Testpassword1'}, follow=True)
        #check that user now exists with new password
        self.assertIsNotNone(authenticate(username='testuser2',password='Testpassword1'))

    def test_signup_confirmation(self):

        c = Client()
        url = reverse('signup')
        response = c.post(url, {'username': 'john', 'password1': 'Boredman1!','password2': 'Boredman1!',
            'email': 'johnsmith@test.com', 'first_name':'john', 'last_name': 'smith'},follow = True)
        self.assertEqual(response.status_code, 200)

        # Check that an email has been sent
        self.assertEqual(len(mail.outbox), 1)
        #check subject line
        self.assertEqual(mail.outbox[0].subject, 'Activate your FullMonte account.')

        # get token and user ID
        token = response.context[0]['token']
        uid = response.context[0]['uid']
        
        url = reverse('activate', args=(uid,token))
        response = c.get(url, follow=True)
        uid = force_text(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=uid)
        self.assertEqual(user.is_active,True)