from django.http import HttpResponseRedirect, HttpResponseBadRequest, JsonResponse
from django.urls import reverse
from django.views import View
from google.oauth2.credentials import Credentials
from google.oauth2 import id_token
from google.auth.transport import requests
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
import google_auth_oauthlib
import secrets
import json
from django.conf import settings


class GoogleCalendarInitView(View):
    def get(self, request):
        state = secrets.token_hex(16)
        redirect_uri = request.build_absolute_uri(reverse('google-calendar-redirect'))
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            settings.GOOGLE_OAUTH2_CLIENT_CONFIG, 
            scopes=['https://www.googleapis.com/auth/calendar.readonly', "openid", "https://www.googleapis.com/auth/userinfo.email"], 
            state=state
        )
        flow.redirect_uri = redirect_uri
        authorization_url, _ = flow.authorization_url(prompt='consent')
        request.session['google_auth_state'] = state
        return HttpResponseRedirect(authorization_url)


class GoogleCalendarRedirectView(View):
    def get(self, request):
        if 'error' in request.GET:
            return HttpResponseBadRequest(request.GET['error'])

        state = request.GET['state']
        if state != request.session.get('google_auth_state'):
            return HttpResponseBadRequest('Invalid state parameter')

        redirect_uri = request.build_absolute_uri(reverse('google-calendar-redirect'))
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            settings.GOOGLE_OAUTH2_CLIENT_CONFIG, 
            scopes=['https://www.googleapis.com/auth/calendar.readonly', "openid", "https://www.googleapis.com/auth/userinfo.email"],
            state=state
        )
        flow.redirect_uri = redirect_uri

        authorization_response = request.build_absolute_uri()
        flow.fetch_token(authorization_response=authorization_response)

        credentials = flow.credentials
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(request.Request())
            request.session['google_auth_credentials'] = credentials.to_json()

        request.session['google_access_token'] = credentials.to_json()

        try:
            id_info = id_token.verify_oauth2_token(
                credentials.id_token, 
                requests.Request(), 
                settings.GOOGLE_OAUTH2_CLIENT_CONFIG['web']['client_id']
            )

            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Invalid issuer')

            user_email = id_info['email']
        except ValueError as ve:
            print("ValueError", ve)
            return HttpResponseBadRequest('Invalid token')

        service = build('calendar', 'v3', credentials=credentials)
        try:
            events = service.events().list(
                calendarId='primary', 
                timeMin='2023-03-01T00:00:00Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            items = events.get('items', [])
            response_data = {
                'email': user_email,
                'events': items
            }
            return JsonResponse(response_data, safe=False)
        except HttpError as error:
            print('An error occurred: %s' % error)
            return HttpResponseBadRequest('Failed to fetch events from Google Calendar')
