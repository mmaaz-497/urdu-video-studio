import type { Metadata } from 'next'
import { Inter, Noto_Nastaliq_Urdu } from 'next/font/google'
import type { ReactNode } from 'react'

import { QueryProvider } from '@/components/providers/query-provider'
import { ThemeProvider } from '@/components/providers/theme-provider'
import { Toaster } from '@/components/ui/sonner'
import '@/app/globals.css'

const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-inter',
  display: 'swap',
})

const notoNastaliqUrdu = Noto_Nastaliq_Urdu({
  subsets: ['arabic'],
  weight: ['400', '700'],
  variable: '--font-urdu',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Urdu Video Studio',
  description: 'Turn an idea into a short Urdu video — write it, review it, watch it come to life.',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${notoNastaliqUrdu.variable} font-sans antialiased`}>
        <QueryProvider>
          <ThemeProvider attribute="class" defaultTheme="system" enableSystem themes={['light', 'dark']}>
            {children}
            <Toaster position="top-center" richColors />
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  )
}
