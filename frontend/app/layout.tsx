/* eslint-disable max-len */
import { Metadata } from 'next'
import '../modules/assets/css/global.css'
import { PropsWithChildren } from 'react'
import NextTopLoader from 'nextjs-toploader'
import { ThemeProvider as ColorThemeProvider } from 'next-themes'
import { ThemeProvider } from '../modules/swap/services/chakra/ThemeProvider'
import { Providers } from '../modules/shared/components/site/providers'

export const metadata: Metadata = {
  title: 'Etanix - DEX aggregator',
  description: `Swap tokens via multiple decentralized exchange.`,
  icons: [
    { rel: 'icon', type: 'image/x-icon', url: '/flower_stereoscopic.png' },
    {
      rel: 'icon',
      type: 'image/png',
      url: '/favicon-light.png',
      media: '(prefers-color-scheme: light)',
    },
    {
      rel: 'icon',
      type: 'image/png',
      url: '/favicon-dark.png',
      media: '(prefers-color-scheme: dark)',
    },
  ],
}

export default function RootLayout({ children }: PropsWithChildren) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script async src="https://w.appzi.io/w.js?token=8TY8k" />
      </head>
      <body
        style={{ marginRight: '0px !important' }} // Required to prevent layout shift introduced by Rainbowkit
        suppressHydrationWarning
      >
        <NextTopLoader color="#7f6ae8" showSpinner={false} />
        <ColorThemeProvider>
          <ThemeProvider>
            <Providers>
                {children}
            </Providers>
          </ThemeProvider>
        </ColorThemeProvider>
      </body>
    </html>
  )
}
