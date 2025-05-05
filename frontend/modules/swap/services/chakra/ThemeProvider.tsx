'use client'

import { ChakraProvider, ThemeTypings } from '@chakra-ui/react'
import { ReactNode, useMemo } from 'react'
import { theme as balTheme } from './themes/bal/bal.theme'

export function ThemeProvider({ children }: { children: ReactNode }) {

  return (
    <ChakraProvider
      cssVarsRoot="body"
      theme={balTheme}
      toastOptions={{ defaultOptions: { position: 'bottom-left' } }}
    >
      {children}
    </ChakraProvider>
  )
}
