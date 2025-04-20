"""Authentication Views for the People core app."""

import copy
import json
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import auth
from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils import crypto
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import requests
from mozilla_django_oidc.utils import (
    absolutify,
)
from mozilla_django_oidc.views import (
    OIDCAuthenticationCallbackView as MozillaOIDCAuthenticationCallbackView,
)
from mozilla_django_oidc.views import (
    OIDCAuthenticationRequestView as MozillaOIDCAuthenticationRequestView,
)
from mozilla_django_oidc.views import (
    OIDCLogoutView as MozillaOIDCOIDCLogoutView,
)

from .backends import OIDCAuthenticationBackend


class OIDCLogoutView(MozillaOIDCOIDCLogoutView):
    """Custom logout view for handling OpenID Connect (OIDC) logout flow.

    Adds support for handling logout callbacks from the identity provider (OP)
    by initiating the logout flow if the user has an active session.

    The Django session is retained during the logout process to persist the 'state' OIDC parameter.
    This parameter is crucial for maintaining the integrity of the logout flow between this call
    and the subsequent callback.
    """

    @staticmethod
    def persist_state(request, state):
        """Persist the given 'state' parameter in the session's 'oidc_states' dictionary

        This method is used to store the OIDC state parameter in the session, according to the
        structure expected by Mozilla Django OIDC's 'add_state_and_verifier_and_nonce_to_session'
        utility function.
        """

        if "oidc_states" not in request.session or not isinstance(
            request.session["oidc_states"], dict
        ):
            request.session["oidc_states"] = {}

        request.session["oidc_states"][state] = {}
        request.session.save()

    def construct_oidc_logout_url(self, request):
        """Create the redirect URL for interfacing with the OIDC provider.

        Retrieves the necessary parameters from the session and constructs the URL
        required to initiate logout with the OpenID Connect provider.

        If no ID token is found in the session, the logout flow will not be initiated,
        and the method will return the default redirect URL.

        The 'state' parameter is generated randomly and persisted in the session to ensure
        its integrity during the subsequent callback.
        """

        oidc_logout_endpoint = self.get_settings("OIDC_OP_LOGOUT_ENDPOINT")

        if not oidc_logout_endpoint:
            return self.redirect_url

        reverse_url = reverse("oidc_logout_callback")
        id_token = request.session.get("oidc_id_token", None)

        if not id_token:
            return self.redirect_url

        query = {
            "id_token_hint": id_token,
            "state": crypto.get_random_string(self.get_settings("OIDC_STATE_SIZE", 32)),
            "post_logout_redirect_uri": absolutify(request, reverse_url),
        }

        self.persist_state(request, query["state"])

        return f"{oidc_logout_endpoint}?{urlencode(query)}"

    def post(self, request):
        """Handle user logout.

        If the user is not authenticated, redirects to the default logout URL.
        Otherwise, constructs the OIDC logout URL and redirects the user to start
        the logout process.

        If the user is redirected to the default logout URL, ensure her Django session
        is terminated.
        """

        logout_url = self.redirect_url

        if request.user.is_authenticated:
            logout_url = self.construct_oidc_logout_url(request)

        # If the user is not redirected to the OIDC provider, ensure logout
        if logout_url == self.redirect_url:
            auth.logout(request)

        return HttpResponseRedirect(logout_url)


class OIDCLogoutCallbackView(MozillaOIDCOIDCLogoutView):
    """Custom view for handling the logout callback from the OpenID Connect (OIDC) provider.

    Handles the callback after logout from the identity provider (OP).
    Verifies the state parameter and performs necessary logout actions.

    The Django session is maintained during the logout process to ensure the integrity
    of the logout flow initiated in the previous step.
    """

    http_method_names = ["get"]

    def get(self, request):
        """Handle the logout callback.

        If the user is not authenticated, redirects to the default logout URL.
        Otherwise, verifies the state parameter and performs necessary logout actions.
        """

        if not request.user.is_authenticated:
            return HttpResponseRedirect(self.redirect_url)

        state = request.GET.get("state")

        if state not in request.session.get("oidc_states", {}):
            msg = "OIDC callback state not found in session `oidc_states`!"
            raise SuspiciousOperation(msg)

        del request.session["oidc_states"][state]
        request.session.save()

        auth.logout(request)

        return HttpResponseRedirect(self.redirect_url)


class OIDCAuthenticationCallbackView(MozillaOIDCAuthenticationCallbackView):
    """Custom callback view for handling the silent login flow."""

    @property
    def failure_url(self):
        """Override the failure URL property to handle silent login flow

        A silent login failure (e.g., no active user session) should not be
        considered as an authentication failure.
        """
        if self.request.session.get("silent", None):
            del self.request.session["silent"]
            self.request.session.save()
            return self.success_url
        return super().failure_url


class OIDCAuthenticationRequestView(MozillaOIDCAuthenticationRequestView):
    """Custom authentication view for handling the silent login flow."""

    def get_extra_params(self, request):
        """Handle 'prompt' extra parameter for the silent login flow

        This extra parameter is necessary to distinguish between a standard
        authentication flow and the silent login flow.
        """
        extra_params = self.get_settings("OIDC_AUTH_REQUEST_EXTRA_PARAMS", None)
        if extra_params is None:
            extra_params = {}
        if request.GET.get("silent") == "true":
            extra_params = copy.deepcopy(extra_params)
            extra_params.update({"prompt": "none"})
            request.session["silent"] = True
            request.session.save()
        return extra_params


@csrf_exempt
@require_POST
def auto_authenticate(request):
    """Endpoint for direct authentication with username and password.
    
    If authentication fails, attempts to register a new user with the provided credentials,
    then retries authentication.
    
    The endpoint expects a JSON body with:
    {
        "username": "user@example.com",
        "password": "their_password",
        "email": "user@example.com",  # Optional
        "firstname": "First",  # Optional
        "lastname": "Last"  # Optional
    }
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        email = data.get('email') or username  # Default to username if email not provided
        firstname = data.get('firstname', '')
        lastname = data.get('lastname', '')
        
        if not username or not password:
            return JsonResponse(
                {'error': 'Username and password are required'},
                status=400
            )
            
        # First attempt: Try to authenticate with existing credentials
        user, auth_error = attempt_authentication(username, password, request)
        
        # If authentication failed, try registering a new user
        if user is None:
            # Register new user in Keycloak
            registration_success, reg_error = register_keycloak_user(username, password, email, firstname, lastname)
            
            if registration_success:
                # Retry authentication with the newly created user
                user, auth_retry_error = attempt_authentication(username, password, request)
                if user is None:
                    auth_error = auth_retry_error  # Update the auth error with the retry error
        
        # If we have a user by now, login was successful
        if user:
            # Log the user in with the specific backend
            auth.login(request, user, backend='core.authentication.backends.OIDCAuthenticationBackend')
            return JsonResponse({'success': True, 'user_id': user.id})
        else:
            error_msg = 'Authentication failed and user registration was not possible'
            if auth_error:
                error_msg += f". Authentication error: {auth_error}"
            if 'reg_error' in locals() and reg_error:
                error_msg += f". Registration error: {reg_error}"
                
            return JsonResponse({'error': error_msg}, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)
    except requests.RequestException as e:
        return JsonResponse(
            {'error': 'Error connecting to authentication server', 'details': str(e)},
            status=500
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def attempt_authentication(username, password, request=None):
    """Attempt to authenticate a user with Keycloak and return the Django user if successful."""
    token_endpoint = settings.OIDC_OP_TOKEN_ENDPOINT
    client_id = settings.OIDC_RP_CLIENT_ID
    client_secret = settings.OIDC_RP_CLIENT_SECRET
    
    token_data = {
        'grant_type': 'password',
        'username': username,
        'password': password,
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': settings.OIDC_RP_SCOPES
    }
    
    try:
        token_response = requests.post(
            token_endpoint,
            data=token_data,
            verify=settings.OIDC_VERIFY_SSL,
            timeout=getattr(settings, 'OIDC_TIMEOUT', None),
            proxies=getattr(settings, 'OIDC_PROXY', None),
        )
        
        # If authentication failed, return None
        if token_response.status_code != 200:
            error_details = "Unknown error"
            try:
                error_data = token_response.json()
                if 'error' in error_data:
                    error_details = error_data.get('error_description', error_data.get('error', 'Unknown error'))
            except:
                error_details = f"HTTP {token_response.status_code}"
                
            return None, error_details
            
        # Extract tokens from response
        tokens = token_response.json()
        access_token = tokens.get('access_token')
        id_token = tokens.get('id_token')
        
        if not access_token or not id_token:
            return None, "Missing tokens in response"
            
        # Use the backend to create/get the user
        backend = OIDCAuthenticationBackend()
        user = backend.get_or_create_user(access_token, id_token, {})
        
        if user:
            # Set session data (will be used when logging in)
            if request is not None:
                request_session = getattr(request, 'session', None)
                if request_session:
                    request_session['oidc_id_token'] = id_token
                    request_session['oidc_access_token'] = access_token
            
            return user, None
        return None, "Failed to create or get user"
    except Exception as e:
        return None, str(e)
    
    return None, "Unknown authentication error"


def register_keycloak_user(username, password, email, firstname, lastname):
    """Register a new user in Keycloak and return True if successful."""
    # Get admin token for Keycloak API access
    admin_token = get_keycloak_admin_token()
    if not admin_token:
        return False, "Failed to obtain admin token"
        
    # Build user registration data
    user_data = {
        "username": username,
        "email": email,
        "enabled": True,
        "firstName": firstname,
        "lastName": lastname,
        "credentials": [
            {
                "type": "password",
                "value": password,
                "temporary": False
            }
        ]
    }
    
    # Make request to Keycloak Admin API to create user
    keycloak_api_url = f"{settings.KEYCLOAK_BASE_URL}/admin/realms/{settings.KEYCLOAK_REALM}/users"
    try:
        response = requests.post(
            keycloak_api_url,
            json=user_data,
            headers={
                'Authorization': f'Bearer {admin_token}',
                'Content-Type': 'application/json'
            },
            verify=settings.OIDC_VERIFY_SSL,
            timeout=getattr(settings, 'OIDC_TIMEOUT', None),
        )
        
        # 201 Created status indicates success
        if response.status_code == 201:
            return True, None
            
        # If we have an error response, try to parse it
        error_msg = "Unknown registration error"
        try:
            error_data = response.json()
            if 'errorMessage' in error_data:
                error_msg = error_data['errorMessage']
        except:
            error_msg = f"HTTP error {response.status_code}"
            
        return False, error_msg
    except Exception as e:
        return False, str(e)


def get_keycloak_admin_token():
    """Get an admin token for Keycloak API access."""
    try:
        # Get settings
        admin_client_id = getattr(settings, 'KEYCLOAK_ADMIN_CLIENT_ID', 'admin-cli')
        admin_username = settings.KEYCLOAK_ADMIN
        admin_password = settings.KEYCLOAK_ADMIN_PASSWORD
        token_url = f"{settings.KEYCLOAK_BASE_URL}/realms/master/protocol/openid-connect/token"
        
        # Make token request
        response = requests.post(
            token_url,
            data={
                'grant_type': 'password',
                'client_id': admin_client_id,
                'username': admin_username,
                'password': admin_password
            },
            verify=settings.OIDC_VERIFY_SSL,
            timeout=getattr(settings, 'OIDC_TIMEOUT', None),
        )
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get('access_token')
    except:
        pass
    
    return None
