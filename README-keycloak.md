# Keycloak Integration Guide

This guide will help you set up Keycloak authentication for the ODL Video Service project.

## Overview

The ODL Video Service uses Keycloak as an OpenID Connect (OIDC) provider for user authentication. Keycloak handles user login, logout, and provides user/group information that Django uses for authorization.

## Prerequisites

- Docker and Docker Compose installed
- Basic understanding of OAuth 2.0/OIDC concepts

## Quick Start

### 1. Start the Services

```bash
# Start all services including Keycloak
docker-compose up -d

# Check that Keycloak is running
docker-compose ps keycloak
```

Keycloak will be available at: `http://kc.odl.local:7080`

### 2. Access Keycloak Admin Console

1. Open your browser and go to `http://kc.odl.local:7080`
2. Click "Administration Console"
3. Login with the default admin credentials:
   - **Username**: `admin`
   - **Password**: `admin`

### 3. Pre-configured Setup

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

### 4. Get the Public Key (Required)

You need to get the public key from your Keycloak instance:

1. Go to Realm Settings → Keys tab
2. Find the RSA key with "RS256" algorithm
3. Click "Public key" button
4. Copy the public key (without the BEGIN/END lines)
5. Update your `.env` file with the key on a single line:

```env
KEYCLOAK_PUBLIC_KEY=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
```

## Environment Configuration

Create/update your `.env` file with these Keycloak settings:

```env
# Keycloak Configuration
KEYCLOAK_SERVER_URL=http://kc.odl.local:7080
KEYCLOAK_REALM=ovs-local
KEYCLOAK_CLIENT_ID=odl-video-app
KEYCLOAK_CLIENT_SECRET=odl-video-secret-2025
KEYCLOAK_PUBLIC_KEY=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...

# Keycloak Service Configuration (for docker-compose)
KEYCLOAK_SVC_HOSTNAME=kc.odl.local
KEYCLOAK_SVC_ADMIN=admin
KEYCLOAK_SVC_ADMIN_PASSWORD=admin
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

### 2. Group/Role Mapping

The application automatically maps Keycloak groups to Django permissions:

- **Admin group** → `is_superuser=True, is_staff=True`
- **Staff group** → `is_staff=True`
- **Other groups** → Regular user permissions

This mapping is handled by the custom pipeline in `odl_video/pipeline.py`.

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
- Verify `KEYCLOAK_CLIENT_ID` matches the client ID in Keycloak
- Check that `KEYCLOAK_CLIENT_SECRET` is correct

#### 3. "Invalid public key" Error
- Get a fresh public key from Keycloak Admin Console
- Ensure the key is on a single line without spaces or line breaks
- Remove `-----BEGIN PUBLIC KEY-----` and `-----END PUBLIC KEY-----` headers

#### 4. "Connection refused" Error
- Check that Keycloak container is running: `docker-compose ps keycloak`
- Verify Keycloak URL is accessible: `curl http://kc.odl.local:7080`

#### 5. Users Can Login But Have No Permissions
- Check that groups are properly configured
- Verify the pipeline function `assign_user_groups` is working
- Check Django logs for pipeline errors

## File Locations

- **Realm Configuration**: `config/keycloak/realms/ovs-local-realm.json`
- **Django Settings**: `odl_video/settings.py`
- **Authentication Pipeline**: `odl_video/pipeline.py`
- **Docker Compose**: `docker-compose.yml` (Keycloak service definition)
