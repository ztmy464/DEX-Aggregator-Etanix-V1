'use client'

import { getChainShortName } from '../config/app.config'
import { NetworkIcon } from '../shared/components/icons/NetworkIcon'
import { GqlChain } from '../shared/services/api/generated/graphql'
import { Box, HStack, Text, Image } from '@chakra-ui/react'
import { GroupBase, chakraComponents, DropdownIndicatorProps } from 'chakra-react-select'
import { ChevronDown, Globe } from 'react-feather'
import { motion } from 'framer-motion'
import { pulseOnceWithDelay } from '../shared/utils/animations'
import { PROJECT_CONFIG } from '../config/getProjectConfig'
import { SelectInput, SelectOption } from '../shared/components/inputs/SelectInput'

type Props = {
  value: GqlChain
  onChange(value: GqlChain): void
  chains?: GqlChain[]
}

function DropdownIndicator({
  ...props
}: DropdownIndicatorProps<SelectOption, false, GroupBase<SelectOption>>) {
  return (
    <chakraComponents.DropdownIndicator {...props}>
      <HStack>
        <Globe size={16} />
        <ChevronDown size={16} />
      </HStack>
    </chakraComponents.DropdownIndicator>
  )
}

export function ChainSelect({ value, onChange, chains = PROJECT_CONFIG.supportedNetworks }: Props) {
  const networkOptions: SelectOption[] = chains.map(chain => ({
    label: (
      <HStack>
        <Image src={`/images/MAINNET.svg`} boxSize={6} />
        <Text>{getChainShortName(chain)}</Text>
      </HStack>
    ),
    value: chain,
  }))

  return (
    <Box animate={pulseOnceWithDelay} as={motion.div} w="full" zIndex="10">
      <SelectInput
        DropdownIndicator={DropdownIndicator}
        id="chain-select"
        onChange={onChange}
        options={networkOptions}
        value={value}
      />
    </Box>
  )
}
