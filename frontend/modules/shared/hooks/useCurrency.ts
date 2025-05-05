'use client'

import { useUserSettings } from '../../user/settings/UserSettingsProvider'
import { useFxRates } from './FxRatesProvider'
import { getFxRates, FxRates, SupportedCurrency, symbolForCurrency } from '../utils/currencies'
import { Numberish, bn, fNum } from '../utils/numbers'

type CurrencyOpts = { withSymbol?: boolean; abbreviated?: boolean; noDecimals?: boolean }

const [
  exchangeRates,
  // poolTags,
  // erc4626Metadata,
  // poolsMetadata,
  // feeManagersMetadata,
] = await Promise.all([
  getFxRates(),
  // getPoolTags(),
  // getErc4626Metadata(),
  // getPoolsMetadata(),
  // getFeeManagersMetadata(),
])
export function _useFxRates(rates: FxRates | undefined) {
  const hasFxRates = !!rates

  function getFxRate(currency: SupportedCurrency): number {
    if (!rates) return 1
    return rates[currency]?.value || 1
  }

  return { hasFxRates, getFxRate }
}

export function useCurrency() {
  const { currency } = useUserSettings()
  
  const { getFxRate, hasFxRates } = _useFxRates(exchangeRates)

  // Converts a USD value to the user's currency value.
  function toUserCurrency(usdVal: Numberish): string {
    const amount = usdVal.toString()
    const fxRate = getFxRate(currency)

    return bn(amount).times(fxRate).toString()
  }

  function formatCurrency(value: string | undefined) {
    const symbol = hasFxRates ? symbolForCurrency(currency) : '$'
    return `${symbol}${value ?? '0'}`
  }

  function parseCurrency(value: string) {
    return value.replace(/^\$/, '')
  }

  // Converts a USD value to the user's currency and formats in fiat style.
  function toCurrency(
    usdVal: Numberish,
    { withSymbol = true, abbreviated = true, noDecimals = false }: CurrencyOpts = {}
  ): string {
    const symbol = hasFxRates ? symbolForCurrency(currency) : '$'
    const convertedAmount = toUserCurrency(usdVal)

    const formattedAmount = fNum(noDecimals ? 'integer' : 'fiat', convertedAmount, { abbreviated })

    if (formattedAmount.startsWith('<')) {
      return withSymbol ? '<' + symbol + formattedAmount.substring(1) : formattedAmount
    }

    return withSymbol ? symbol + formattedAmount : formattedAmount
  }

  return { toCurrency, formatCurrency, parseCurrency }
}
