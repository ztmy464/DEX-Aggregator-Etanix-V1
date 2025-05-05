import {
  fetchAndMapMetadata,
  lowerCaseAddresses,
} from '../shared/utils/fetchAndLowercaseAddresses'
import { Address } from 'viem'
/*
远程下载一个 JSON 文件（Hook 配置文件），并且把里面的地址字段全部小写处理后，返回一组结构化的 HooksMetadata 数据 
 */
const HOOKS_METADATA_URL =
  'https://raw.githubusercontent.com/balancer/metadata/refs/heads/main/hooks/index.json'

export type HooksMetadata = {
  id: string
  name: string
  description: string
  learnMore?: string
  addresses: Record<string, Address[]> // chainId -> addresses[]
}

export async function getHooksMetadata(): Promise<HooksMetadata[] | undefined> {
  return fetchAndMapMetadata<HooksMetadata>(HOOKS_METADATA_URL, lowerCaseAddresses)
}
