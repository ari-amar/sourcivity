import { redirect } from 'next/navigation'

export default function HomePage() {
  // Redirect to search page as the main landing
  redirect('/search')
}