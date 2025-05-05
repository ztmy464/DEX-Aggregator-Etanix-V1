'use client'
import {
  Button,
  HStack,
  Heading,
  Popover,
  PopoverArrow,
  PopoverBody,
  PopoverCloseButton,
  PopoverContent,
  PopoverHeader,
  PopoverTrigger,
  VStack,
  Text,
  ButtonProps,
  useDisclosure,
  Box,
  Checkbox,
  CheckboxGroup,
  Stack,
  Switch,
} from '@chakra-ui/react'
import { useUserSettings } from './UserSettingsProvider'
import { fNum } from '../../shared/utils/numbers'
import { AlertTriangle, Settings } from 'react-feather'
import { CurrencySelect } from './CurrencySelect'
import { EnableSignaturesSelect, SlippageInput } from './UserSettings'
// import { getDefaultProportionalSlippagePercentage } from '../../
// shared/utils/slippage'
// import { Pool } from '../../pool/pool.types'
import { EnableTxBundleSetting } from './EnableTxBundlesSetting'


// Define the available DEXes
const AVAILABLE_EXCHANGES = [
  { id: 'Uniswap_V2', label: 'Uniswap V2' },
  { id: 'Sushiswap_V2', label: 'Sushiswap V2' },
  { id: 'Uniswap_V3', label: 'Uniswap V3' },
  { id: 'Pancakeswap_V3', label: 'Pancakeswap V3' },
  { id: 'Curve', label: 'Curve' },
  { id: 'Balancer_V3', label: 'Balancer V3' },
];

// Add selectedExchanges to props
interface TransactionSettingsProps extends ButtonProps {
  selectedExchanges: string[];
  setSelectedExchanges: (exchanges: string[]) => void;
}

export function TransactionSettings({
  selectedExchanges,
  setSelectedExchanges,
  ...props
}: TransactionSettingsProps) {
  const { slippage, setSlippage } = useUserSettings()
    // Handle exchange selection change
  const handleExchangeChange = (values: string[]) => {
    setSelectedExchanges(values);
  };

  return (
    <Popover isLazy placement="bottom-end">
      <PopoverTrigger>
        <Button variant="tertiary" {...props}>
          <HStack textColor="grayText">
            <Text color="grayText" fontSize="xs">
              {fNum('slippage', slippage)}
            </Text>
            <Settings size={16} />
          </HStack>
        </Button>
      </PopoverTrigger>
      <PopoverContent>
        <PopoverArrow bg="background.level3" />
        <PopoverCloseButton />
        <PopoverHeader>
          <Heading size="md">Transaction settings</Heading>
        </PopoverHeader>
        <PopoverBody p="md">
          <VStack align="start" spacing="lg" w="full">
            <VStack align="start" w="full">
              <Heading size="sm">Currency</Heading>
              <CurrencySelect id="transaction-settings-currency-select" />
            </VStack>
            <VStack align="start" w="full">
              <Heading size="sm">Slippage</Heading>
              <SlippageInput setSlippage={setSlippage} slippage={slippage} />
            </VStack>
            <Box w="full">
              <Heading pb="xs" size="sm">
              available DEXs
              </Heading>
                {/* 添加分隔线和留白 */}
                <Box 
                  borderBottom="1px" 
                  borderColor="gray.100" 
                  mb="3"
                />
              <CheckboxGroup 
                colorScheme="blue" 
                value={selectedExchanges}
                onChange={handleExchangeChange}
              >
                <Stack spacing="sm">
                  {AVAILABLE_EXCHANGES.map((exchange) => (
                    <Checkbox 
                      key={exchange.id} 
                      value={exchange.id}
                    >
                      {exchange.label}
                    </Checkbox>
                  ))}
                </Stack>
              </CheckboxGroup>
               {/* 全选开关 */}
               <Box 
                  w="full" 
                  display="flex" 
                  justifyContent="space-between" 
                  alignItems="center"
                  pt="sm"
                  borderTop="1px"
                  borderColor="gray.200"
                >
                  <Box fontSize="sm">Select All</Box>
                  <Switch 
                    colorScheme="green"
                    size="md"
                    isChecked={selectedExchanges.length === AVAILABLE_EXCHANGES.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        // 全选所有DEX
                        setSelectedExchanges(AVAILABLE_EXCHANGES.map(exchange => exchange.id));
                      } else {
                        // 取消全选
                        setSelectedExchanges([]);
                      }
                    }}
                  />
                </Box>
            </Box>
          </VStack>
        </PopoverBody>
      </PopoverContent>
    </Popover>
  )
}

interface ProportionalTransactionSettingsProps extends ButtonProps {
  slippage: string
  setSlippage: (value: string) => void
}

export function ProportionalTransactionSettings({
  slippage,
  setSlippage,
  ...props
}: ProportionalTransactionSettingsProps) {
  const { isOpen, onOpen, onClose } = useDisclosure()

  const defaultProportionalSlippagePercentage = '0'

  return (
    <Popover isLazy isOpen={isOpen} onClose={onClose} placement="bottom-end">
      <PopoverTrigger>
        <Button onClick={onOpen} variant="tertiary" {...props}>
          <HStack textColor="grayText">
            <AlertTriangle size={16} />
            <Text color="grayText" fontSize="xs">
              {fNum('slippage', slippage)}
            </Text>
            <Settings size={16} />
          </HStack>
        </Button>
      </PopoverTrigger>
      <PopoverContent>
        <PopoverArrow bg="background.level3" />
        <PopoverCloseButton />
        <PopoverHeader>
          <Heading size="md">Transaction settings</Heading>
        </PopoverHeader>
        <PopoverBody p="md">
          <VStack align="start" spacing="lg" w="full">
            <VStack align="start" w="full">
              <Heading size="sm">Currency</Heading>
              <CurrencySelect id="transaction-settings-currency-select" />
            </VStack>
            <VStack align="start" w="full">
              <HStack>
                <Heading size="sm">Slippage</Heading>
                <Popover>
                  <PopoverTrigger>
                    <AlertTriangle size={16} />
                  </PopoverTrigger>
                </Popover>
              </HStack>
              <SlippageInput setSlippage={setSlippage} slippage={slippage} />
            </VStack>

            <Box w="full">
              <Heading pb="xs" size="sm">
                Use Signatures
              </Heading>
            </Box>
          </VStack>
        </PopoverBody>
      </PopoverContent>
    </Popover>
  )
}
