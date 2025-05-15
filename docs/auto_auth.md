# Auto Authentication

## Overview

The Auto Authentication feature provides a streamlined way to authenticate users by integrating with Kadmap API and passing credentials through URL parameters. This approach is particularly useful for:

- External applications that integrate with the system
- Testing environments
- Creating deep links for specific user accounts
- Simplified onboarding processes

## How It Works

The auto authentication system works in three stages:

1. **Frontend**: A dedicated route (`/auto_auth`) accepts authentication parameters
2. **Kadmap Integration**: The system fetches user data from Kadmap API
3. **Backend**: The server authenticates the user with the data received from Kadmap

### Authentication Flow

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│             │         │             │         │             │         │             │
│   Browser   │ ──────► │  Frontend   │ ──────► │ Kadmap API  │ ──────► │   Backend   │
│             │         │             │         │             │         │             │
└─────────────┘         └─────────────┘         └─────────────┘         └─────────────┘
      │                                                                        │
      │                           Authentication Result                        │
      └────────────────────────────────────◄───────────────────────────────────┘
```

## Implementation Details

### Frontend Component

The auto authentication route is implemented in `src/frontend/src/features/auth/AutoAuthRoute.tsx`. Key features include:

- Accepts URL parameters for Kadmap integration
- Fetches user data from Kadmap API
- Displays a loading spinner during authentication
- Shows helpful error messages if authentication fails
- Provides a link to the regular login page if needed

#### URL Parameters

The component accepts the following URL parameters:

- `kadmap_api_url`: The base URL for Kadmap API
- `vfs_base_url`: The base URL for VFS
- `workspace_id`: The workspace identifier
- `user_id`: The user identifier in Kadmap

### Backend Implementation

The backend handles the auto authentication in `src/backend/core/authentication/views.py` through the `auto_authenticate` function. This endpoint:

1. Receives user data fetched from Kadmap API
2. Authenticates the user with the provided information
3. Returns detailed error information if the process fails

## Usage

To use the auto authentication feature, create a URL with the following format:

```
http://{baseUrl}/auto_auth?kadmap_api_url={kadmapApiUrl}&vfs_base_url={vfsBaseUrl}&workspace_id={workspaceId}&user_id={userId}&user_KID={userKID}
```

### Example

```
http://localhost:3000/auto_auth?kadmap_api_url=http%3A%2F%2F192.168.30.77%3A19090%2Fapi%2Fv1&vfs_base_url=http%3A%2F%2F192.168.30.77%3A8001&workspace_id=b77911b0-6c89-4136-a1b9-d50ecaed5597&user_id=891e9432-6655-413e-8840-27ad23c9b223&user_KID=adminmanager%40kadmap.kadmaphq
```

## Important Notes

- The system requires all four parameters (kadmap_api_url, vfs_base_url, workspace_id, and user_id) to be present
- User information is fetched from Kadmap API using the provided user_id
- Authentication uses the Kadmap user data (userKID as username/email, userId as password)
- All requests are made over a secure connection to protect credentials in production
- URL parameters should be properly URL-encoded to handle special characters

## Error Messages

The system provides detailed error messages to help diagnose authentication issues:

- If missing required parameters, the error will indicate which ones are missing
- If Kadmap API connection fails, the error will indicate the connection issue
- If authentication fails, the error will indicate the reason

## Troubleshooting

If you encounter authentication failures, check:

1. All required URL parameters are provided
2. Kadmap API URL is accessible and responding
3. User ID exists in the Kadmap system
4. VFS base URL is correct and accessible

## Security Considerations

While convenient, this authentication method has security implications:

- URL parameters may be logged in browser history or server logs
- Consider using this primarily for development, testing or controlled environments
- In production, use with caution and ensure proper access controls
- Ensure Kadmap API endpoints are properly secured 