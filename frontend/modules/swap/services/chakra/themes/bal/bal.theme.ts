import { ThemeTypings, extendTheme } from '@chakra-ui/react'
import { colors, primaryTextColor } from './colors'
import { getTokens } from '../../../../../shared/services/chakra/themes/base/tokens'
import { getComponents } from '../../../../../shared/services/chakra/themes/base/components'
import {
  fonts,
  styles,
  themeConfig,
} from '../../../../../shared/services/chakra/themes/base/foundations'
import { getSemanticTokens } from '../../../../../shared/services/chakra/themes/base/semantic-tokens'
import { proseTheme } from '../../../../../shared/services/chakra/themes/base/prose'

const tokens = getTokens(colors, primaryTextColor)
const components = getComponents(tokens, primaryTextColor)
const semanticTokens = getSemanticTokens(tokens, colors)

export const balTheme = {
  config: themeConfig,
  fonts,
  styles,
  colors,
  semanticTokens,
  components,
}

export const theme = extendTheme(balTheme, proseTheme) as ThemeTypings
