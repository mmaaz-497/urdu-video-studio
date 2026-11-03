import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const SESSION_COOKIE_NAME = 'session_id'

export function middleware(request: NextRequest) {
  const sessionId = request.cookies.get(SESSION_COOKIE_NAME)?.value

  if (!sessionId) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('next', request.nextUrl.pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/create', '/review', '/videos', '/videos/:path*'],
}
