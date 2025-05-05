/* eslint-disable react-hooks/exhaustive-deps */
import { useEffect, useState } from 'react'
/* 
跳过（skip）组件第一次挂载（mount）时就发送网络请求
*/
export function useSkipInitialQuery(queryVariables: Record<any, any>) {
  const [initQueryVarsAreSet, setInitQueryVarsAreSet] = useState(false)
  const [skipQuery, setSkipQuery] = useState(true)

  useEffect(() => {
    setInitQueryVarsAreSet(true)
  }, [JSON.stringify(queryVariables)])

  useEffect(() => {
    if (initQueryVarsAreSet) setSkipQuery(false)
  }, [JSON.stringify(queryVariables)])

  return skipQuery
}
