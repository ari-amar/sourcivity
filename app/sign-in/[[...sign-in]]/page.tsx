'use client'

import { SignIn } from '@clerk/nextjs'

export default function SignInPage() {
  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-4rem)] bg-gray-50">
      <SignIn />
    </div>
  )
}
