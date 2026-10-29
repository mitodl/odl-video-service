# Keycloak Integration Guide

This guide will help you set up Keycloak authentication for the ODL Video Service project.

## Overview

The ODL Video Service uses Keycloak as an OpenID Connect (OIDC) provider for user authentication. Keycloak handles user login, logout, and provides user/group information that Django uses for authorization.

## Prerequisites

- Docker and Docker Compose installed
- Basic understanding of OAuth 2.0/OIDC concepts

## Quick Start

### 1. First-time setup

For local development OIDC signing key pair files are pre-generated and placed in `config/keycloak/tls`. The [Local Realm JSON](config/keycloak/realms/ovs-local-realm.json#1930) already contains the correct values for  `privateKey` and `certificate` from [Key](config/keycloak/tls/oidc-signing.key) and [Certificate](config/keycloak/tls/oidc-signing.crt) respectively.

```
"privateKey": ["MIIEowIBAAKCAQEAkVcc5QcK9biP2TWBO3P1ZlxbhDpsr..."]
"certificate": ["MIICpDCCAYwCCQD5UHLf1MqmDDANBgkqhkiG9w0BAQsFA..."]
```

### 2. Start the Services

```bash
# Start all services including Keycloak
docker-compose up -d

# Check that Keycloak is running
docker-compose ps keycloak
```

### Add `/etc/hosts` alias for Keycloak

If one doesn’t already exist, add an alias to `/etc/hosts` for Keycloak. We have standardized this alias to kc.odl.local. Your `/etc/hosts` entry should look like this:
```bash
127.0.0.1.   kc.odl.local
```

Keycloak will be available at: `http://kc.odl.local:7080`

### 3. Access Keycloak Admin Console

1. Open your browser and go to `https://kc.odl.local:7443`
2. Login with the default admin credentials:
   - **Username**: `admin`
   - **Password**: `admin`

### 4. Pre-configured Setup

The project comes with a pre-configured realm called `ovs-local` that includes:

#### **Pre-defined Users:**
- **admin/admin** - Administrator user (Admin group)
- **staff/staff** - Staff user (Staff group)
- **user/user** - Regular user (no specific group)

#### **Pre-defined Groups:**
- **Admin** - Full administrative access
- **Staff** - Staff-level access
- **User** - Basic user access

#### **Pre-configured Client:**
- **Client ID**: `odl-video-app`
- **Client Secret**: `odl-video-secret-2025`

#### **Pre-configured Signing**
- **Private Key**: `MIIEowIBAAKCAQEAkVcc5QcK9biP2TWBO3P1ZlxbhDpsr...`
- **Certificate**: `MIICpDCCAYwCCQD5UHLf1MqmDDANBgkqhkiG9w0BAQsFA...`


### 5. Signing Keys

The app verifies access tokens against the realm's published signing keys, which it fetches from `/protocol/openid-connect/certs` next to `SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL`. Nothing needs to be copied out of Keycloak, and rotating the realm key doesn't require a config change.

## Environment Configuration

Create/update your `.env` file with these Keycloak settings:

```env
# Runtime OIDC login — consumed by social-auth-app-django.
SOCIAL_AUTH_KEYCLOAK_KEY=odl-video-app
SOCIAL_AUTH_KEYCLOAK_SECRET=odl-video-secret-2025
SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL=http://kc.odl.local:7080/realms/ovs-local/protocol/openid-connect/auth
SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL=http://kc.odl.local:7080/realms/ovs-local/protocol/openid-connect/token

# Admin-API access — consumed by the moira-to-keycloak migration commands.
KEYCLOAK_SERVER_URL=http://kc.odl.local:7080
KEYCLOAK_REALM=ovs-local
KEYCLOAK_SVC_ADMIN=admin
KEYCLOAK_SVC_ADMIN_PASSWORD=admin

# Local Keycloak container bootstrap.
KEYCLOAK_SVC_HOSTNAME=kc.odl.local
KEYCLOAK_PORT=7080
KEYCLOAK_SSL_PORT=7443
```

## How Authentication Works

### 1. User Login Flow

1. User visits the application
2. Clicks login or accesses protected content
3. Django redirects to Keycloak login page
4. User enters Keycloak credentials
5. Keycloak redirects back to Django with authorization code
6. Django exchanges code for access token
7. Django creates/updates user account with Keycloak data

### 2. Django Permissions

Keycloak authenticates users but does **not** manage Django's `is_staff` /
`is_superuser` flags. Those are set manually via the Django admin or shell and
are preserved across logins. The raw `user_groups` claim from Keycloak is still
stored on the social user's `extra_data` (see `SOCIAL_AUTH_KEYCLOAK_EXTRA_DATA`
in `odl_video/settings.py`) but nothing acts on it.

## Testing Authentication

### 1. Test with Pre-defined Users

1. Go to `http://localhost:8089`
2. Click "Login"
3. Use one of the pre-defined users:
   - `admin/admin`
   - `staff/staff`
   - `user/user`

### 2. Create New Users

In Keycloak Admin Console:

1. Go to Users → Add user
2. Fill in username, email, first name, last name
3. Save user
4. Go to Credentials tab → Set password
5. (Optional) Go to Groups tab → Join groups

## Troubleshooting

### Common Issues

#### 1. "Invalid redirect URI" Error
- Check that redirect URIs in Keycloak client match your application URL
- Ensure Web Origins are set correctly

#### 2. "Invalid client" Error
- Verify `SOCIAL_AUTH_KEYCLOAK_KEY` matches the client ID in Keycloak
- Check that `SOCIAL_AUTH_KEYCLOAK_SECRET` is correct

#### 3. Token signature, "Unable to find a signing key", or "Fail to fetch data from the url" Error
- Check that the app container can reach the realm JWKS: `docker compose exec web curl http://kc.odl.local:7080/realms/ovs-local/protocol/openid-connect/certs`. Running the curl from the host doesn't show whether the app can reach Keycloak.

#### 4. "Connection refused" Error
- Check that Keycloak container is running: `docker-compose ps keycloak`
- Verify Keycloak URL is accessible: `curl http://kc.odl.local:7080`

#### 5. Users Can Login But Have No Permissions
- `is_staff` / `is_superuser` are set manually in Django admin or shell; log in
  as an existing superuser and promote the new user from there.

## File Locations

- **Realm Configuration**: `config/keycloak/realms/ovs-local-realm.json`
- **Django Settings**: `odl_video/settings.py`
- **Docker Compose**: `docker-compose.yml` (Keycloak service definition)
