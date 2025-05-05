// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "../../src/interfaces/IERC20.sol";
import {FullMath} from "../../src/uniswap-v3/FullMath.sol";
// swap wbtc to eth
// forge test --match-path test/aggregator/UniV3Swap_weth_wbtc.t.sol --fork-url $FORK_URL -vvv
interface IUniswapV3Pool {
    function swap(
        address recipient,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96,
        bytes calldata data
    ) external returns (int256 amount0, int256 amount1);

    function slot0()
        external
        view
        returns (
            uint160 sqrtPriceX96,
            int24 tick,
            uint16 observationIndex,
            uint16 observationCardinality,
            uint16 observationCardinalityNext,
            uint8 feeProtocol,
            bool unlocked
        );

    function liquidity() external view returns (uint128);
    
    function token0() external view returns (address);
    function token1() external view returns (address);
}

contract UniswapV3PoolTest is Test {
    IUniswapV3Pool public pool;
    IERC20 public wbtc;
    IERC20 public weth;
    
    address constant POOL_ADDRESS = 0xCBCdF9626bC03E24f779434178A73a0B4bad62eD;
    address constant WBTC_ADDRESS = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599;
    address constant WETH_ADDRESS = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    
    // Whale addresses for getting tokens
    address constant WETH_WHALE = 0x8EB8a3b98659Cce290402893d0123abb75E3ab28;
    address constant WBTC_WHALE = 0x9ff58f4fFB29fA2266Ab25e75e2A8b3503311656;
    
    uint256 constant WETH_AMOUNT = 1111110 ether; // 10 WETH

    // token0 (X)
    uint256 private constant WBTC_DECIMALS = 1e8;
    // token1 (Y)
    uint256 private constant WETH_DECIMALS = 1e18;
    // 1 << 96 = 2 ** 96
    uint256 private constant Q96 = 1 << 96;
    
    function setUp() public {
        pool = IUniswapV3Pool(POOL_ADDRESS);
        wbtc = IERC20(WBTC_ADDRESS);
        weth = IERC20(WETH_ADDRESS);
    }
    
    function test_GetPoolInfo() public view {
        
        // Get slot0 information
        (
            uint160 sqrtPriceX96,
            int24 tick,
            uint16 observationIndex,
            uint16 observationCardinality,
            uint16 observationCardinalityNext,
            uint8 feeProtocol,
            bool unlocked
        ) = pool.slot0();
        
        // Get liquidity information
        uint128 liq = pool.liquidity();
        
        // Log all information
        console.log("Pool Information:");
        console.log("sqrtPriceX96:", sqrtPriceX96);
        console.log("tick:", tick);
        console.log("observationIndex:", observationIndex);
        console.log("observationCardinality:", observationCardinality);
        console.log("observationCardinalityNext:", observationCardinalityNext);
        console.log("feeProtocol:", feeProtocol);
        console.log("unlocked:", unlocked);
        console.log("liquidity:", liq);

        uint256 price = 0;
        price = FullMath.mulDiv(sqrtPriceX96, sqrtPriceX96, Q96) / Q96;
        console2.log("price %e", price);
    }
    
    function test_SwapWethForWbtc() public {
        // First get some WETH from a whale
        deal(address(weth), address(this), WETH_AMOUNT);
        
        // Get balance before swap
        uint256 wethBalanceBefore = weth.balanceOf(address(this));
        uint256 wbtcBalanceBefore = wbtc.balanceOf(address(this));
        
        // Approve tokens for the pool
        weth.approve(POOL_ADDRESS, type(uint256).max);
        
        // Callback will be executed during the swap, so prepare the pool
        uint256 wethToSwap = 2000 ether; // Swap 1 WETH
        // We need to create a callback contract to handle the swap
        UniswapV3SwapCallback callbackContract = new UniswapV3SwapCallback(WETH_ADDRESS, WBTC_ADDRESS);
        weth.transfer(address(callbackContract), wethToSwap);
        
        // The swap itself
        bool zeroForOne = false; // swapping token1 (WETH) for token0 (WBTC)
        int256 amountSpecified = int256(wethToSwap); // positive for exact input, negative for exact output
        // uint160 MIN_SQRT_RATIO = 4295128739;
        uint160 MAX_SQRT_RATIO = 1461446703485210103287273052203988822378723970342;
        uint160 sqrtPriceLimitX96 = MAX_SQRT_RATIO-1; // 0 for no price limit
        
        console.log("Performing swap of", wethToSwap / 1e18, "WETH for WBTC");
        
        // We're going to call the swap through our callback contract
        (int256 amount0, int256 amount1) = callbackContract.executeSwap(
            POOL_ADDRESS,
            zeroForOne,
            amountSpecified,
            sqrtPriceLimitX96
        );
        
        // Get wbtc from the callback contract
        // uint256 receivedWbtc = wbtc.balanceOf(address(callbackContract));
        
        // Get balance after swap
        uint256 wethBalanceAfter = weth.balanceOf(address(this));
        uint256 wbtcBalanceAfter = wbtc.balanceOf(address(this));
        
        console.log("After swap:");
        assertLt(wethBalanceAfter, wethBalanceBefore);
        assertGt(wbtcBalanceAfter, wbtcBalanceBefore);
        
        // Log the swap results
        console.log("amount0 (WBTC received):", uint256(-amount0));
        console.log("amount1 (WETH spent):", uint256(amount1));
    }
}

// Helper contract to handle Uniswap V3 callbacks
contract UniswapV3SwapCallback {
    IERC20 public immutable token0;
    IERC20 public immutable token1;
    
    constructor(address _token1, address _token0) {
        token0 = IERC20(_token0);
        token1 = IERC20(_token1);
    }
    
    // Function to execute the swap
    function executeSwap(
        address poolAddress,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96
    ) external returns (int256 amount0, int256 amount1) { 
        (amount0, amount1) = IUniswapV3Pool(poolAddress).swap(
            address(this),
            zeroForOne,
            amountSpecified,
            sqrtPriceLimitX96, 
            abi.encode(msg.sender)
        );
        // If amount0 is negative, it means this contract received token0 (WBTC) from the pool
        if (amount0 < 0) {
            // Transfer the received token0 (WBTC) back to the user who initiated the swap
            // Use uint256(-amount0) to get the positive amount received
            token0.transfer(msg.sender, uint256(-amount0));
        }
        if (amount1 < 0) {
           token1.transfer(msg.sender, uint256(-amount1));
        }

       return (amount0, amount1);
    }
    
    // Callback function that Uniswap V3 will call during the swap
    function uniswapV3SwapCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata data
    ) external {
        // Decode the callback data to get the caller
        address caller = abi.decode(data, (address));
        
        // If amount0 is positive, we need to pay token0 to the pool
        if (amount0Delta > 0) {
            token0.transfer(msg.sender, uint256(amount0Delta));
        }
        
        // If amount1 is positive, we need to pay token1 to the pool
        if (amount1Delta > 0) {
            token1.transfer(msg.sender, uint256(amount1Delta));
        }
    }
}