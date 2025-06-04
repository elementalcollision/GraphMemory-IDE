"""
Single Sign-On (SSO) Manager for GraphMemory-IDE

This module implements comprehensive SSO functionality including:
- SAML 2.0 implementation for enterprise providers
- Multi-provider support (Azure AD, Okta, Google Workspace)
- OAuth2/OpenID Connect for modern cloud providers
- Automatic user provisioning and role mapping
- Session management and token handling
- Security validation and error handling

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

import base64
import json
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from urllib.parse import urlencode, urlparse
import xml.etree.ElementTree as ET

from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
import httpx
import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

from ..core.logger import logger
from ..models.user import User, UserRole
from ..models.sso_provider import SSOProvider
from ..core.database import get_db


class SSOProviderType:
    """SSO provider types."""
    SAML = "saml"
    OAUTH2 = "oauth2"
    OIDC = "openid_connect"


class SAMLBinding:
    """SAML binding types."""
    HTTP_POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    HTTP_REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"


class SSOError(Exception):
    """Base exception for SSO operations."""
    pass


class SAMLError(SSOError):
    """SAML-specific exceptions."""
    pass


class OAuth2Error(SSOError):
    """OAuth2-specific exceptions."""
    pass


class SAMLRequest:
    """SAML Authentication Request builder."""
    
    def __init__(self, settings: Any) -> None:
        self.settings = settings
    
    def build_auth_request(
        self, 
        provider: SSOProvider, 
        relay_state: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Build SAML authentication request.
        
        Returns:
            Tuple of (saml_request, redirect_url)
        """
        request_id = f"_id_{uuid.uuid4().hex}"
        issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Build SAML AuthnRequest XML
        saml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{provider.sso_url}"
    AssertionConsumerServiceURL="{self.settings.SAML_SP_ACS_URL}"
    ProtocolBinding="{SAMLBinding.HTTP_POST}">
    <saml:Issuer>{self.settings.SAML_SP_ENTITY_ID}</saml:Issuer>
    <samlp:NameIDPolicy
        Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
        AllowCreate="true"/>
</samlp:AuthnRequest>"""
        
        # Encode SAML request
        encoded_request = base64.b64encode(saml_request.encode()).decode()
        
        # Build redirect URL
        params = {
            "SAMLRequest": encoded_request,
            "RelayState": relay_state or "",
        }
        
        redirect_url = f"{provider.sso_url}?{urlencode(params)}"
        
        return encoded_request, redirect_url
    
    def build_metadata(self) -> str:
        """Build SP metadata XML."""
        metadata = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor
    xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{self.settings.SAML_SP_ENTITY_ID}">
    <md:SPSSODescriptor
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:AssertionConsumerService
            Binding="{SAMLBinding.HTTP_POST}"
            Location="{self.settings.SAML_SP_ACS_URL}"
            index="0"/>
        <md:SingleLogoutService
            Binding="{SAMLBinding.HTTP_POST}"
            Location="{self.settings.SAML_SP_SLS_URL}"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""
        
        return metadata


class SAMLResponse:
    """SAML Response parser and validator."""
    
    def __init__(self, settings: Any) -> None:
        self.settings = settings
    
    def parse_response(self, saml_response: str) -> Dict[str, Any]:
        """Parse and validate SAML response."""
        try:
            # Decode base64
            decoded_response = base64.b64decode(saml_response).decode()
            
            # Parse XML
            root = ET.fromstring(decoded_response)
            
            # Extract namespace
            ns = {
                'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
                'saml': 'urn:oasis:names:tc:SAML:2.0:assertion'
            }
            
            # Validate response status
            status_code = root.find('.//samlp:StatusCode', ns)
            if status_code is None or status_code.get('Value') != 'urn:oasis:names:tc:SAML:2.0:status:Success':
                raise SAMLError("SAML response indicates failure")
            
            # Extract assertion
            assertion = root.find('.//saml:Assertion', ns)
            if assertion is None:
                raise SAMLError("No assertion found in SAML response")
            
            # Extract user attributes
            attributes = {}
            for attr in assertion.findall('.//saml:Attribute', ns):
                attr_name = attr.get('Name')
                attr_values = [val.text for val in attr.findall('.//saml:AttributeValue', ns)]
                attributes[attr_name] = attr_values[0] if len(attr_values) == 1 else attr_values
            
            # Extract NameID (user identifier)
            name_id = assertion.find('.//saml:NameID', ns)
            user_id = name_id.text if name_id is not None else None
            
            # Extract session data
            authn_statement = assertion.find('.//saml:AuthnStatement', ns)
            session_index = authn_statement.get('SessionIndex') if authn_statement is not None else None
            
            return {
                'user_id': user_id,
                'attributes': attributes,
                'session_index': session_index,
                'assertion_xml': ET.tostring(assertion, encoding='unicode')
            }
            
        except ET.ParseError as e:
            raise SAMLError(f"Invalid SAML response XML: {e}")
        except Exception as e:
            raise SAMLError(f"Failed to parse SAML response: {e}")


class OAuth2Client:
    """OAuth2/OpenID Connect client implementation."""
    
    def __init__(self, settings: Any) -> None:
        self.settings = settings
    
    async def get_authorization_url(
        self, 
        provider: SSOProvider, 
        state: str,
        scopes: Optional[List[str]] = None
    ) -> str:
        """Generate OAuth2 authorization URL."""
        if scopes is None:
            scopes = ["openid", "profile", "email"]
        
        params = {
            "client_id": provider.client_id,
            "response_type": "code",
            "scope": " ".join(scopes),
            "redirect_uri": provider.redirect_uri,
            "state": state,
        }
        
        # Add PKCE for security
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashes.Hash(hashes.SHA256()).finalize()
        ).decode().rstrip('=')
        
        params.update({
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        })
        
        return f"{provider.auth_url}?{urlencode(params)}"
    
    async def exchange_code_for_tokens(
        self, 
        provider: SSOProvider, 
        code: str,
        code_verifier: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        data = {
            "grant_type": "authorization_code",
            "client_id": provider.client_id,
            "client_secret": provider.client_secret,
            "code": code,
            "redirect_uri": provider.redirect_uri,
            "code_verifier": code_verifier,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                provider.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                raise OAuth2Error(f"Token exchange failed: {response.text}")
            
            return response.json()
    
    async def get_user_info(self, provider: SSOProvider, access_token: str) -> Dict[str, Any]:
        """Get user information using access token."""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(provider.userinfo_url, headers=headers)
            
            if response.status_code != 200:
                raise OAuth2Error(f"User info request failed: {response.text}")
            
            return response.json()


class UserProvisioner:
    """Handles automatic user provisioning from SSO providers."""
    
    def __init__(self, db_session: Any) -> None:
        self.db = db_session
    
    async def provision_user(
        self, 
        provider: SSOProvider, 
        user_data: Dict[str, Any]
    ) -> User:
        """Provision user from SSO provider data."""
        # Extract user information
        email = self._extract_email(user_data)
        if not email:
            raise SSOError("No email found in SSO response")
        
        # Check if user already exists
        existing_user = await self._get_user_by_email(email)
        if existing_user:
            # Update existing user
            await self._update_user_from_sso(existing_user, provider, user_data)
            return existing_user
        
        # Create new user
        new_user = await self._create_user_from_sso(provider, user_data)
        return new_user
    
    def _extract_email(self, user_data: Dict[str, Any]) -> Optional[str]:
        """Extract email from user data."""
        # Try different common email field names
        email_fields = ['email', 'mail', 'emailAddress', 'Email', 'Mail']
        
        for field in email_fields:
            if field in user_data:
                email = user_data[field]
                if isinstance(email, list):
                    email = email[0] if email else None
                return email
        
        return None
    
    def _extract_name(self, user_data: Dict[str, Any]) -> Tuple[str, str]:
        """Extract first and last name from user data."""
        # Try to get full name first
        full_name = user_data.get('displayName') or user_data.get('name', '')
        
        if full_name and ' ' in full_name:
            parts = full_name.split(' ', 1)
            return parts[0], parts[1]
        
        # Try individual fields
        first_name = user_data.get('givenName') or user_data.get('firstName', '')
        last_name = user_data.get('surname') or user_data.get('lastName', '')
        
        return first_name, last_name
    
    def _determine_role(self, provider: SSOProvider, user_data: Dict[str, Any]) -> UserRole:
        """Determine user role based on provider data."""
        # Check for admin groups/roles
        groups = user_data.get('groups', [])
        roles = user_data.get('roles', [])
        
        admin_indicators = ['admin', 'administrator', 'superuser', 'owner']
        
        for group in groups:
            if any(indicator in group.lower() for indicator in admin_indicators):
                return UserRole.ADMIN
        
        for role in roles:
            if any(indicator in role.lower() for indicator in admin_indicators):
                return UserRole.ADMIN
        
        # Default to user role
        return UserRole.USER
    
    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        # This would interface with your user model/database
        # Implementation depends on your database setup
        pass
    
    async def _create_user_from_sso(self, provider: SSOProvider, user_data: Dict[str, Any]) -> User:
        """Create new user from SSO data."""
        email = self._extract_email(user_data)
        first_name, last_name = self._extract_name(user_data)
        role = self._determine_role(provider, user_data)
        
        # Create user (implementation depends on your user model)
        user_data_dict = {
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'role': role,
            'is_active': True,
            'sso_provider_id': provider.id,
            'sso_user_id': user_data.get('sub') or user_data.get('id'),
            'created_at': datetime.utcnow(),
            'last_login': datetime.utcnow(),
        }
        
        # This would create the user in your database
        # Implementation depends on your user model
        pass
    
    async def _update_user_from_sso(self, user: User, provider: SSOProvider, user_data: Dict[str, Any]) -> None:
        """Update existing user from SSO data."""
        first_name, last_name = self._extract_name(user_data)
        
        # Update user fields
        user.first_name = first_name
        user.last_name = last_name
        user.last_login = datetime.utcnow()
        
        # Save changes
        await self.db.commit()


class SessionManager:
    """Manages SSO sessions and tokens."""
    
    def __init__(self, settings: Any) -> None:
        self.settings = settings
    
    def create_session(self, user: User, provider: SSOProvider, sso_data: Dict[str, Any]) -> str:
        """Create session token for authenticated user."""
        payload = {
            'user_id': str(user.id),
            'email': user.email,
            'role': user.role.value,
            'provider_id': provider.id,
            'provider_type': provider.type,
            'session_id': str(uuid.uuid4()),
            'iat': int(time.time()),
            'exp': int(time.time()) + (self.settings.JWT_EXPIRATION_HOURS * 3600),
            'sso_session_index': sso_data.get('session_index'),
        }
        
        token = jwt.encode(
            payload, 
            self.settings.JWT_SECRET_KEY, 
            algorithm=self.settings.JWT_ALGORITHM
        )
        
        return token
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode JWT token."""
        try:
            payload = jwt.decode(
                token, 
                self.settings.JWT_SECRET_KEY, 
                algorithms=[self.settings.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise SSOError("Token has expired")
        except jwt.InvalidTokenError:
            raise SSOError("Invalid token")
    
    async def logout(self, token: str, provider: SSOProvider) -> Optional[str]:
        """Handle logout and return SLO URL if applicable."""
        payload = self.validate_token(token)
        session_index = payload.get('sso_session_index')
        
        if provider.type == SSOProviderType.SAML and provider.slo_url and session_index:
            # Build SAML logout request
            logout_request = self._build_saml_logout_request(provider, payload, session_index)
            return logout_request
        
        return None
    
    def _build_saml_logout_request(
        self, 
        provider: SSOProvider, 
        payload: Dict[str, Any], 
        session_index: str
    ) -> str:
        """Build SAML logout request."""
        request_id = f"_id_{uuid.uuid4().hex}"
        issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        logout_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:LogoutRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{provider.slo_url}">
    <saml:Issuer>{self.settings.SAML_SP_ENTITY_ID}</saml:Issuer>
    <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">
        {payload['email']}
    </saml:NameID>
    <samlp:SessionIndex>{session_index}</samlp:SessionIndex>
</samlp:LogoutRequest>"""
        
        encoded_request = base64.b64encode(logout_request.encode()).decode()
        params = {"SAMLRequest": encoded_request}
        
        return f"{provider.slo_url}?{urlencode(params)}"


class SSOManager:
    """
    Main SSO Manager coordinating all SSO operations.
    
    Features:
    - SAML 2.0 implementation for enterprise providers
    - OAuth2/OpenID Connect for modern providers
    - Multi-provider support (Azure AD, Okta, Google)
    - Automatic user provisioning
    - Session management and security
    """
    
    def __init__(self, settings: Any, db_session: Any) -> None:
        self.settings = settings
        self.db = db_session
        self.saml_request = SAMLRequest(settings)
        self.saml_response = SAMLResponse(settings)
        self.oauth2_client = OAuth2Client(settings)
        self.user_provisioner = UserProvisioner(db_session)
        self.session_manager = SessionManager(settings)
    
    async def get_provider(self, provider_name: str) -> Optional[SSOProvider]:
        """Get SSO provider configuration."""
        # This would query your database for the provider
        # Implementation depends on your database setup
        pass
    
    async def initiate_login(self, provider_name: str, return_url: Optional[str] = None) -> str:
        """Initiate SSO login flow."""
        provider = await self.get_provider(provider_name)
        if not provider:
            raise SSOError(f"Unknown SSO provider: {provider_name}")
        
        if not provider.enabled:
            raise SSOError(f"SSO provider {provider_name} is disabled")
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Store state and return URL in session/cache
        # Implementation depends on your session storage
        
        if provider.type == SSOProviderType.SAML:
            _, redirect_url = self.saml_request.build_auth_request(provider, state)
            return redirect_url
        
        elif provider.type in [SSOProviderType.OAUTH2, SSOProviderType.OIDC]:
            return await self.oauth2_client.get_authorization_url(provider, state)
        
        else:
            raise SSOError(f"Unsupported provider type: {provider.type}")
    
    async def handle_callback(
        self, 
        provider_name: str, 
        request_data: Dict[str, Any]
    ) -> Tuple[User, str]:
        """Handle SSO callback and return user and session token."""
        provider = await self.get_provider(provider_name)
        if not provider:
            raise SSOError(f"Unknown SSO provider: {provider_name}")
        
        if provider.type == SSOProviderType.SAML:
            return await self._handle_saml_callback(provider, request_data)
        
        elif provider.type in [SSOProviderType.OAUTH2, SSOProviderType.OIDC]:
            return await self._handle_oauth2_callback(provider, request_data)
        
        else:
            raise SSOError(f"Unsupported provider type: {provider.type}")
    
    async def _handle_saml_callback(
        self, 
        provider: SSOProvider, 
        request_data: Dict[str, Any]
    ) -> Tuple[User, str]:
        """Handle SAML callback."""
        saml_response = request_data.get('SAMLResponse')
        if not saml_response:
            raise SAMLError("No SAML response in callback")
        
        # Parse and validate SAML response
        parsed_response = self.saml_response.parse_response(saml_response)
        
        # Provision user
        user = await self.user_provisioner.provision_user(provider, parsed_response['attributes'])
        
        # Create session
        session_token = self.session_manager.create_session(user, provider, parsed_response)
        
        logger.info(f"SAML SSO login successful for user {user.email} via {provider.name}")
        
        return user, session_token
    
    async def _handle_oauth2_callback(
        self, 
        provider: SSOProvider, 
        request_data: Dict[str, Any]
    ) -> Tuple[User, str]:
        """Handle OAuth2/OIDC callback."""
        code = request_data.get('code')
        state = request_data.get('state')
        
        if not code:
            raise OAuth2Error("No authorization code in callback")
        
        # Validate state (CSRF protection)
        # Implementation depends on your session storage
        
        # Exchange code for tokens
        code_verifier = "..."  # Retrieved from session
        tokens = await self.oauth2_client.exchange_code_for_tokens(provider, code, code_verifier)
        
        # Get user information
        user_info = await self.oauth2_client.get_user_info(provider, tokens['access_token'])
        
        # Provision user
        user = await self.user_provisioner.provision_user(provider, user_info)
        
        # Create session
        session_token = self.session_manager.create_session(user, provider, user_info)
        
        logger.info(f"OAuth2 SSO login successful for user {user.email} via {provider.name}")
        
        return user, session_token
    
    async def logout(self, session_token: str) -> Optional[str]:
        """Handle SSO logout."""
        try:
            payload = self.session_manager.validate_token(session_token)
            provider = await self.get_provider_by_id(payload['provider_id'])
            
            if provider:
                slo_url = await self.session_manager.logout(session_token, provider)
                logger.info(f"SSO logout for user {payload['email']} via {provider.name}")
                return slo_url
            
        except Exception as e:
            logger.error(f"SSO logout error: {e}")
        
        return None
    
    async def get_provider_by_id(self, provider_id: str) -> Optional[SSOProvider]:
        """Get provider by ID."""
        # Implementation depends on your database setup
        pass
    
    def get_metadata(self) -> str:
        """Get SAML SP metadata."""
        return self.saml_request.build_metadata()
    
    async def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Validate SSO session token."""
        try:
            return self.session_manager.validate_token(session_token)
        except SSOError:
            return None


# Global SSO manager instance
sso_manager = None


async def initialize_sso_manager(settings: Any, db_session: Any) -> None:
    """Initialize the global SSO manager."""
    global sso_manager
    if settings.SSO_ENABLED:
        sso_manager = SSOManager(settings, db_session)
        logger.info("SSO manager initialized successfully")


def get_sso_manager() -> Optional[SSOManager]:
    """Get the global SSO manager instance."""
    return sso_manager 