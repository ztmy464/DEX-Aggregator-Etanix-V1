'use client'

import { PropsWithChildren,use } from 'react'
import SwapLayout from '../../../modules/swap/SwapLayout'
import { getSwapPathParams } from '../../../modules/swap/getSwapPathParams'
import { DefaultPageContainer } from '../../../modules/swap/components/containers/DefaultPageContainer'
import { SwapProviderProps } from '../../../modules/swap/SwapProvider'

type Props = PropsWithChildren<{
  params: Promise<{ slug?: string[] }> | { slug?: string[] }
}>

export default function Layout({ params, children }: Props) {
  const resolvedParams = use(params as Promise<{ slug?: string[] }>)
  const pathParams = getSwapPathParams(resolvedParams.slug)
  const swapProps: SwapProviderProps = {
    pathParams,
  }
  return (
    <DefaultPageContainer minH="100vh">
      <SwapLayout props={swapProps}> {children} </SwapLayout>
    </DefaultPageContainer>
  )
}
