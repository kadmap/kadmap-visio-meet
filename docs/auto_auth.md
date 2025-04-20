# Auto Authentication

## Overview

The Auto Authentication feature provides a streamlined way to authenticate users by directly passing credentials through URL parameters. This approach is particularly useful for:

- External applications that integrate with the system
- Testing environments
- Creating deep links for specific user accounts
- Simplified onboarding processes

## How It Works

The auto authentication system works in two stages:

1. **Frontend**: A dedicated route (`/auto_auth`) accepts authentication parameters and makes a request to the backend.
2. **Backend**: The server attempts to authenticate the user with the provided credentials. If authentication fails, it will attempt to register a new user with those credentials and then authenticate them.

### Authentication Flow

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│             │         │             │         │             │
│   Browser   │ ──────► │  Frontend   │ ──────► │   Backend   │
│             │         │             │         │             │
└─────────────┘         └─────────────┘         └─────────────┘
      │                                                │
      │                                                │
      │              Authentication Result             │
      └────────────────────────────────────◄──────────┘
```

## Implementation Details

### Frontend Component

The auto authentication route is implemented in `src/frontend/src/features/auth/AutoAuthRoute.tsx`. Key features include:

- Accepts URL parameters for authentication 
- Displays a loading spinner during authentication
- Shows helpful error messages if authentication fails
- Provides a link to the regular login page if needed

#### URL Parameters

The component accepts the following URL parameters:

- `username`: The user's username
- `password`: The user's password
- `email`: User's email
- `firstname`: User's first name
- `lastname`: User's last name

### Backend Implementation

The backend handles the auto authentication in `src/backend/core/authentication/views.py` through the `auto_authenticate` function. This endpoint:

1. Attempts to authenticate with the provided credentials
2. If authentication fails, tries to register a new user with those credentials
3. Attempts authentication again with the newly created account
4. Returns detailed error information if the process fails


## Usage

To use the auto authentication feature, create a URL with the following format:

```
http://{baseUrl}/auto_auth?username={username}&password={password}&email={email}&firstname={First}&lastname={Last}
```

### Example

```
http://localhost:3000/auto_auth?username=newuser&password=testpassword&email=newuser@example.com&firstname=New&lastname=User
```

## Important Notes

- If a user with the provided username already exists but the password is incorrect, the authentication will fail.
- If a user with the provided username already exists, the registration step will fail.
- All requests are made over a secure connection to protect credentials in production.
- This feature should be used carefully in production environments as it passes credentials through URL parameters.

## Error Messages

The system provides detailed error messages to help diagnose authentication issues:

- If authentication fails, the error will indicate the reason (e.g., invalid credentials)
- If registration fails, the error will specify why (e.g., user already exists)

## Troubleshooting

If you encounter the error "Authentication failed and user registration was not possible", check:

1. If the username already exists in the system
2. If the provided password is correct for existing users
3. That all required fields are properly formatted

## Security Considerations

While convenient, this authentication method has security implications:

- URL parameters may be logged in browser history or server logs
- Consider using this primarily for development, testing or controlled environments
- In production, use with caution and ensure proper access controls 