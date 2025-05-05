/* eslint-disable react-hooks/exhaustive-deps */
import {
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  Box,
  HStack,
  Text,
  VStack,
  Button,
  Card,
  useDisclosure,
  AccordionIcon,
  Alert,
  AlertTitle,
  AlertDescription,
  CardFooter,
  CardBody,
} from '@chakra-ui/react'
import { usePriceImpact } from './PriceImpactProvider'
import { fNum } from '../shared/utils/numbers'
import { ReactNode, useEffect } from 'react'
import { PriceImpactAcceptModal } from './PriceImpactAcceptModal'
import { getPriceImpactExceedsLabel } from './price-impact.utils'

interface PriceImpactAccordionProps {
  accordionButtonComponent: ReactNode
  accordionPanelComponent: ReactNode
  isDisabled?: boolean
}
export function RoutesAccordion({
  accordionButtonComponent,
  accordionPanelComponent,
  isDisabled,
}: PriceImpactAccordionProps) {

  return (
    <Box w="full">
      <Accordion allowToggle variant="button" w="full">
        <AccordionItem isDisabled={isDisabled} shadow={isDisabled ? 'none' : undefined} w="full">
          <h2>
            <AccordionButton>
              <Box as="span" flex="1" textAlign="left">
                {accordionButtonComponent}
              </Box>
              <HStack>
                <Text fontSize="sm">
                  Routes Details
                </Text>
                <AccordionIcon />
              </HStack>
            </AccordionButton>
          </h2>
          <AccordionPanel py="md">{accordionPanelComponent}</AccordionPanel>
        </AccordionItem>
      </Accordion>
     
    </Box>
  )
}
