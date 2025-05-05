type HumanAmount = `${number}`;
type Address = `0x${string}`;
const MAX_UINT256 = BigInt("115792089237316195423570985008687907853269984665640564039457584007913129639935");
type InputToken = {
    address: Address;
    decimals: number;
};
type InputAmount = InputToken & {
    rawAmount: bigint;
};
export { type HumanAmount, type Address, MAX_UINT256, type InputToken, type InputAmount };