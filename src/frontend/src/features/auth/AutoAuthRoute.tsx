import { css } from '@/styled-system/css'
import { useEffect, useState } from 'react'
import { authUrl } from './utils/authUrl'
import { fetchApi } from '@/api/fetchApi'

export const AutoAuthRoute = () => {
  const [isLoading, setIsLoading] = useState(true)
  const [message, setMessage] = useState('Preparing your account')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Extract query parameters from URL
    const params = new URLSearchParams(window.location.search)
    const kadmap_api_url = params.get('kadmap_api_url')
    const vfs_base_url = params.get('vfs_base_url')
    const workspace_id = params.get('workspace_id')
    const user_id = params.get('user_id')

    if (kadmap_api_url && vfs_base_url && workspace_id && user_id) {
      authenticateUser(kadmap_api_url, vfs_base_url, workspace_id, user_id)
    } else {
      setMessage('Error: Missing kadmap_api_url, vfs_base_url, workspace_id, or user_id')
      setError('kadmap_api_url, vfs_base_url, workspace_id, and user_id are required')
      setIsLoading(false)
    }
  }, [])
  
  const authenticateUser = async (
    kadmap_api_url?: string | null,
    vfs_base_url?: string | null,
    workspace_id?: string | null,
    user_id?: string | null
  ) => {
    try {
      if (kadmap_api_url) {
        setMessage('Connecting to Kadmap...')
        
        // Make API call to kadmap_api_url
        const kadmapResponse = await fetch(`${kadmap_api_url}/directory/users/${user_id}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        })
        
        if (!kadmapResponse.ok) {
          throw new Error('Failed to connect to Kadmap')
        }
        
        const kadmapResponseJson = await kadmapResponse.json()
        const kadmapData = kadmapResponseJson.data

        console.log(kadmapData)
        
        // Process kadmap data as needed
        const email = kadmapData.userKID
        const username = kadmapData.userKID
        const fullName = kadmapData.fullName.split(' ')
        const firstname = fullName[0]
        const lastname = fullName[1]
        const password = kadmapData.userId

        setMessage(`Authenticating as ${username}...`)
        
        // Create the authentication payload
        const authPayload = {
          username,
          password,
          email,
          firstname,
          lastname,
          kadmap_api_url,
          vfs_base_url,
          workspace_id,
          user_id
        }
        
        // Send credentials to backend authentication endpoint
        await fetchApi('/auto-authenticate/', {
          method: 'POST',
          body: JSON.stringify(authPayload),
          headers: {
            'Content-Type': 'application/json'
          }
        })
        
        // If successful, redirect to home or designated page
        setMessage('Authentication successful! Redirecting...')
        
        setTimeout(() => {
          window.location.href = '/'
        }, 1000)
      }
    } catch (err) {
      // If there's an error, show the fallback auth link
      console.error('Authentication error:', err)
      setError('Authentication failed. Please try again or use the login page.')
      setMessage('Authentication failed')
      setIsLoading(false)
    }
  }

  return (
    <div className={css({
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      padding: '2rem',
      textAlign: 'center'
    })}>
      {/* Loader instead of heading */}
      {isLoading && (
        <div 
          className={css({
            marginBottom: '1rem',
            width: '40px',
            height: '40px',
            border: '4px solid rgba(0, 0, 0, 0.1)',
            borderTopColor: 'blue.500',
            borderRadius: '50%'
          })}
          style={{ animation: 'spin 1s linear infinite' }}
        />
      )}
      <p className={css({
        fontSize: 'lg',
        color: 'greyscale.600'
      })}>
        {message}
      </p>
      {isLoading && (
        <div className={css({
          marginTop: '1rem'
        })}>
          Loading...
        </div>
      )}
      {error && (
        <div className={css({
          marginTop: '2rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem'
        })}>
          <p className={css({
            color: 'red.500',
            fontSize: 'md'
          })}>
            {error}
          </p>
          <a
            href={authUrl()}
            className={css({
              color: 'blue.500',
              textDecoration: 'underline'
            })}
          >
            Go to login page
          </a>
        </div>
      )}
    </div>
  )
} 