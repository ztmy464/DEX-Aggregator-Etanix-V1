'use client'

import { SupportedCurrency } from '../../shared/utils/currencies'
import { Circle, HStack, Text } from '@chakra-ui/react'
import { GroupBase, OptionBase, Select, SingleValue } from 'chakra-react-select'
import { ReactNode } from 'react'
import Image from 'next/image'
import { useUserSettings } from './UserSettingsProvider'
import { getSelectStyles } from '../../shared/services/chakra/custom/chakra-react-select'

interface CurrencyOption extends OptionBase {
  label: ReactNode
  value: SupportedCurrency
}

const currencyIconMap: Record<SupportedCurrency, string> = {
  [SupportedCurrency.USD]: '/images/currencies/USD.svg',
  [SupportedCurrency.EUR]: '/images/currencies/EUR.svg',
  [SupportedCurrency.GBP]: '/images/currencies/GBP.svg',
  [SupportedCurrency.JPY]: '/images/currencies/JPY.svg',
  [SupportedCurrency.CNY]: '/images/currencies/CNY.svg',
  [SupportedCurrency.BTC]: '/images/currencies/BTC.svg',
  [SupportedCurrency.ETH]: '/images/currencies/ETH.svg',
}

const options: CurrencyOption[] = Object.values(SupportedCurrency).map(currency => ({
  label: (
    <HStack>
      <Circle bg="background.level2" size={6}>
        <Image alt={currency} height={20} src={currencyIconMap[currency]} width={20} />
      </Circle>
      <Text>{currency}</Text>
    </HStack>
  ),
  value: currency,
}))

export function CurrencySelect({ id }: { id: string }) {
  const { currency, setCurrency } = useUserSettings()
  const chakraStyles = getSelectStyles<CurrencyOption>()

  function handleChange(newOption: SingleValue<CurrencyOption>) {
    if (newOption) setCurrency(newOption.value)
  }

  const _value = options.find(option => option.value === currency)

  return (
    <Select<CurrencyOption, false, GroupBase<CurrencyOption>>
      chakraStyles={chakraStyles}
      instanceId={id}
      onChange={handleChange}
      options={options}
      value={_value}
    />
  )
}
