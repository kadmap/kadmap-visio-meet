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
    const username = params.get('username')
    const password = params.get('password')
    const email = params.get('email')
    const firstname = params.get('firstname')
    const lastname = params.get('lastname')

    if (username && password) {
      authenticateUser(username, password, email, firstname, lastname)
    } else {
      setMessage('Error: Missing username or password')
      setError('Username and password are required')
      setIsLoading(false)
    }
  }, [])
  
  const authenticateUser = async (
    username: string, 
    password: string, 
    email?: string | null, 
    firstname?: string | null, 
    lastname?: string | null
  ) => {
    try {
      setMessage(`Authenticating as ${username}...`)
      
      // Create the authentication payload
      const authPayload = {
        username,
        password,
        // Only include additional fields if they exist
        ...(email && { email }),
        ...(firstname && { firstname }),
        ...(lastname && { lastname })
      }
      
      // Send credentials to backend authentication endpoint - note the trailing slash
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